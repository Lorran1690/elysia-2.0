package org.elysia.mobile;

import android.content.ClipData;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.Signature;
import android.net.Uri;
import android.os.Build;
import android.os.SystemClock;
import android.provider.Settings;
import androidx.core.content.FileProvider;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.URL;
import java.security.MessageDigest;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;
import javax.net.ssl.HttpsURLConnection;
import org.json.JSONObject;

/** Explicit updates of this installed app; the bridge accepts no URL or path. */
@CapacitorPlugin(name = "ElysiaUpdates")
public final class ElysiaUpdatesPlugin extends Plugin {
    private static final String PACKAGE_ID = "org.elysia.mobile";
    private static final String CHANNEL = "https://raw.githubusercontent.com/Lorran1690/elysia-2.0/refs/heads/feature/media-creation/artifacts/android/";
    static final String APK_URL = CHANNEL + "Elysia-Android.apk";
    private static final String LATEST_URL = CHANNEL + "latest.json";
    private static final long MAX_APK = 100L * 1024 * 1024;
    private static final long DOWNLOAD_TIMEOUT_MS = 15L * 60 * 1000;
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final AtomicBoolean busy = new AtomicBoolean(false);
    private volatile Candidate candidate;
    private volatile Verified verified;

    static final class Candidate {
        final String version, source, sha256;
        final long build, bytes;

        Candidate(String version, long build, String source, long bytes, String sha256) {
            this.version = version;
            this.build = build;
            this.source = source;
            this.bytes = bytes;
            this.sha256 = sha256;
        }

        JSObject json() {
            return new JSObject().put("version", version).put("build", build)
                .put("source_sha", source).put("tag", "android-" + source.substring(0, 12))
                .put("bytes", bytes).put("sha256", sha256)
                .put("release_url", "https://github.com/Lorran1690/elysia-2.0/tree/feature/media-creation/artifacts/android");
        }
    }

    private static final class Verified {
        final Candidate candidate;
        final File file;

        Verified(Candidate candidate, File file) {
            this.candidate = candidate;
            this.file = file;
        }
    }

    private static final class UpdateFailure extends Exception {
        UpdateFailure(String message) { super(message); }
    }

    private interface Work { JSObject run() throws Exception; }

    private void run(PluginCall call, Work work) {
        if (!busy.compareAndSet(false, true)) {
            call.reject("Uma atualização já está em andamento.");
            return;
        }
        worker.execute(() -> {
            try {
                call.resolve(work.run());
            } catch (UpdateFailure error) {
                call.reject(error.getMessage());
            } catch (Exception error) {
                // Do not expose native paths, exception dumps or private state.
                call.reject("Não foi possível concluir a atualização. Verifique a conexão e o espaço disponível e tente novamente.");
            } finally {
                busy.set(false);
            }
        });
    }

    @Override
    protected void handleOnDestroy() {
        worker.shutdownNow();
    }

    @PluginMethod
    public void info(PluginCall call) {
        try { call.resolve(status(candidate)); }
        catch (Exception error) { call.reject("Não foi possível consultar a versão instalada."); }
    }

    @PluginMethod
    public void check(PluginCall call) {
        run(call, () -> {
            HttpsURLConnection connection = connect(new URL(LATEST_URL));
            Candidate found = null;
            try {
                int code = connection.getResponseCode();
                // The first public build may precede publication of its descriptor.
                if (code != 404) {
                    requireSuccess(code);
                    if (connection.getContentLengthLong() > 65536) {
                        throw new UpdateFailure("Os dados da atualização são grandes demais.");
                    }
                    try (InputStream input = connection.getInputStream()) {
                        found = parseManifest(new JSONObject(new String(readBounded(input, 65536), java.nio.charset.StandardCharsets.UTF_8)));
                    }
                }
            } finally { connection.disconnect(); }
            Verified old = verified;
            if (old != null && (found == null || !same(old.candidate, found))) {
                old.file.delete();
                verified = null;
            }
            candidate = found;
            return status(found);
        });
    }

    @PluginMethod
    public void download(PluginCall call) {
        run(call, () -> {
            Candidate selected = candidate;
            if (selected == null) throw new UpdateFailure("Verifique as atualizações primeiro.");
            File folder = new File(getContext().getCacheDir(), "exports/updates");
            if (!folder.isDirectory() && !folder.mkdirs()) throw new IOException("cache");
            File part = new File(folder, UUID.randomUUID() + ".part");
            File ready = new File(folder, UUID.randomUUID() + ".apk");
            HttpsURLConnection connection = null;
            try {
                connection = connect(new URL(APK_URL));
                requireSuccess(connection.getResponseCode());
                long announced = connection.getContentLengthLong();
                if (announced >= 0 && announced != selected.bytes) {
                    throw new UpdateFailure("O tamanho do download não corresponde à publicação. Tente verificar novamente.");
                }
                long received = 0, started = SystemClock.elapsedRealtime(), tick = started;
                MessageDigest digest = MessageDigest.getInstance("SHA-256");
                progress("downloading", 0, selected.bytes);
                try (InputStream input = connection.getInputStream(); FileOutputStream output = new FileOutputStream(part)) {
                    byte[] buffer = new byte[65536];
                    int count;
                    while ((count = input.read(buffer)) != -1) {
                        if (Thread.currentThread().isInterrupted() || SystemClock.elapsedRealtime() - started > DOWNLOAD_TIMEOUT_MS) {
                            throw new UpdateFailure("O download foi interrompido. Nenhum aplicativo foi instalado.");
                        }
                        received += count;
                        if (received > selected.bytes || received > MAX_APK) {
                            throw new UpdateFailure("O arquivo recebido é maior que a publicação verificada.");
                        }
                        output.write(buffer, 0, count);
                        digest.update(buffer, 0, count);
                        long now = SystemClock.elapsedRealtime();
                        if (now - tick >= 150) {
                            progress("downloading", received, selected.bytes);
                            tick = now;
                        }
                    }
                    output.getFD().sync();
                }
                if (received != selected.bytes || !hex(digest.digest()).equals(selected.sha256)) {
                    throw new UpdateFailure("A integridade do APK falhou. Nenhum aplicativo foi instalado. Verifique e baixe novamente.");
                }
                if (!part.renameTo(ready)) throw new IOException("rename");
                verifyApk(ready, selected);
                Verified previous = verified;
                verified = new Verified(selected, ready);
                if (previous != null) previous.file.delete();
                progress("verified", received, selected.bytes);
                return new JSObject().put("verified", true).put("version", selected.version)
                    .put("build", selected.build).put("bytes", selected.bytes).put("sha256", selected.sha256);
            } catch (Exception error) {
                ready.delete();
                throw error;
            } finally {
                part.delete();
                if (connection != null) connection.disconnect();
            }
        });
    }

    @PluginMethod
    public void install(PluginCall call) {
        run(call, () -> {
            Verified selected = verified;
            if (selected == null || candidate == null || !same(selected.candidate, candidate)) {
                throw new UpdateFailure("Baixe e verifique a atualização antes de instalar.");
            }
            verifyHash(selected.file, selected.candidate);
            verifyApk(selected.file, selected.candidate);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O && !getContext().getPackageManager().canRequestPackageInstalls()) {
                Intent permission = new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:" + PACKAGE_ID));
                permission.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                getContext().startActivity(permission);
                throw new UpdateFailure("Autorize a Elysia a instalar atualizações nas configurações do Android, volte e toque em Instalar novamente. O APK já está verificado.");
            }
            Uri uri = FileProvider.getUriForFile(getContext(), PACKAGE_ID + ".fileprovider", selected.file);
            Intent installer = new Intent(Intent.ACTION_VIEW);
            installer.setDataAndType(uri, "application/vnd.android.package-archive");
            installer.setClipData(ClipData.newRawUri("Atualização Elysia", uri));
            installer.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_ACTIVITY_NEW_TASK);
            // Android shows its own confirmation. Cancellation never removes the current app.
            getContext().startActivity(installer);
            return new JSObject().put("launched", true);
        });
    }

    private JSObject status(Candidate selected) throws Exception {
        PackageInfo installed = installed(0);
        return new JSObject().put("supported", true).put("installed", true)
            .put("current_version", installed.versionName).put("current_build", versionCode(installed))
            .put("current_source", BuildConfig.ELYSIA_SOURCE_SHA)
            .put("status", selected == null ? "up-to-date" : "available")
            .put("candidate", selected == null ? JSONObject.NULL : selected.json());
    }

    private PackageInfo installed(int flags) throws Exception {
        if (!PACKAGE_ID.equals(getContext().getPackageName())) throw new UpdateFailure("Aplicativo de atualização inválido.");
        return getContext().getPackageManager().getPackageInfo(PACKAGE_ID, flags);
    }

    private Candidate parseManifest(JSONObject data) throws Exception {
        JSONObject apk = data.getJSONObject("apk");
        String version = data.getString("version"), source = data.getString("source_sha"), hash = apk.getString("sha256");
        long build = positiveInteger(data.get("build")), bytes = positiveInteger(apk.get("bytes"));
        if (!"elysia-android-update-v1".equals(data.getString("format")) || !validVersion(version)
                || !source.matches("[a-f0-9]{40}") || !hash.matches("[a-f0-9]{64}")
                || build > Integer.MAX_VALUE || bytes > MAX_APK
                || !"Elysia-Android.apk".equals(apk.getString("name")) || !APK_URL.equals(apk.getString("url"))) {
            throw new UpdateFailure("A publicação não contém uma atualização válida da Elysia.");
        }
        PackageInfo current = installed(0);
        if (!newer(version, build, current.versionName, versionCode(current))) return null;
        return new Candidate(version, build, source, bytes, hash);
    }

    private static long positiveInteger(Object value) throws UpdateFailure {
        if (!(value instanceof Number)) throw new UpdateFailure("Número inválido na publicação.");
        Number number = (Number) value;
        long result = number.longValue();
        if (result <= 0 || number.doubleValue() != (double) result) throw new UpdateFailure("Número inválido na publicação.");
        return result;
    }

    static boolean validVersion(String value) {
        return value != null && value.matches("(0|[1-9][0-9]{0,8})\\.(0|[1-9][0-9]{0,8})\\.(0|[1-9][0-9]{0,8})");
    }

    static boolean newer(String next, long nextBuild, String current, long currentBuild) {
        if (nextBuild <= currentBuild || !validVersion(next) || !validVersion(current)) return false;
        String[] a = next.split("\\."), b = current.split("\\.");
        for (int i = 0; i < 3; i++) {
            long left = Long.parseLong(a[i]), right = Long.parseLong(b[i]);
            if (left != right) return left > right;
        }
        return true;
    }

    private static boolean same(Candidate a, Candidate b) {
        return a.build == b.build && a.bytes == b.bytes && a.source.equals(b.source)
            && a.version.equals(b.version) && a.sha256.equals(b.sha256);
    }

    private static long versionCode(PackageInfo info) {
        return Build.VERSION.SDK_INT >= Build.VERSION_CODES.P ? info.getLongVersionCode() : (info.versionCode & 0xffffffffL);
    }

    private void verifyApk(File file, Candidate expected) throws Exception {
        int flags = Build.VERSION.SDK_INT >= Build.VERSION_CODES.P ? PackageManager.GET_SIGNING_CERTIFICATES : PackageManager.GET_SIGNATURES;
        PackageManager manager = getContext().getPackageManager();
        PackageInfo downloaded = manager.getPackageArchiveInfo(file.getAbsolutePath(), flags), current = installed(flags);
        if (downloaded == null || !PACKAGE_ID.equals(downloaded.packageName)
                || versionCode(downloaded) != expected.build || !expected.version.equals(downloaded.versionName)
                || !newer(downloaded.versionName, versionCode(downloaded), current.versionName, versionCode(current))) {
            throw new UpdateFailure("O APK não corresponde ao aplicativo ou à versão esperada. Nenhuma instalação foi iniciada.");
        }
        if (!sameSigners(signers(current), signers(downloaded))) {
            throw new UpdateFailure("A assinatura da atualização é diferente da Elysia instalada. Nenhuma instalação foi iniciada.");
        }
    }

    private static Set<String> signers(PackageInfo info) throws Exception {
        Signature[] signatures;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            signatures = info.signingInfo == null ? null : info.signingInfo.getApkContentsSigners();
        } else { signatures = info.signatures; }
        Set<String> fingerprints = new HashSet<>();
        if (signatures != null) for (Signature signature : signatures) {
            fingerprints.add(hex(MessageDigest.getInstance("SHA-256").digest(signature.toByteArray())));
        }
        return fingerprints;
    }

    static boolean sameSigners(Set<String> current, Set<String> downloaded) {
        return !current.isEmpty() && current.equals(downloaded);
    }

    static void verifyHash(File file, Candidate expected) throws Exception {
        if (!file.isFile() || file.length() != expected.bytes) throw new UpdateFailure("O tamanho do APK não confere. Baixe a atualização novamente.");
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream input = new FileInputStream(file)) {
            byte[] buffer = new byte[65536];
            int count;
            while ((count = input.read(buffer)) != -1) digest.update(buffer, 0, count);
        }
        if (!hex(digest.digest()).equals(expected.sha256)) {
            throw new UpdateFailure("A integridade do APK falhou. Nenhuma instalação foi iniciada.");
        }
    }

    static String hex(byte[] bytes) {
        StringBuilder out = new StringBuilder(bytes.length * 2);
        for (byte value : bytes) out.append(String.format(Locale.ROOT, "%02x", value & 0xff));
        return out.toString();
    }

    private void progress(String stage, long downloaded, long total) {
        JSObject value = new JSObject().put("stage", stage).put("downloaded", downloaded).put("total", total);
        getActivity().runOnUiThread(() -> notifyListeners("progress", value));
    }

    static boolean allowedUrl(URL url) {
        String host = url.getHost().toLowerCase(Locale.ROOT);
        return "https".equals(url.getProtocol()) && (url.getPort() == -1 || url.getPort() == 443)
            && url.getUserInfo() == null && url.getRef() == null
            && (host.equals("raw.githubusercontent.com") || host.equals("github.com")
                || host.equals("release-assets.githubusercontent.com") || host.equals("objects.githubusercontent.com"));
    }

    private static HttpsURLConnection connect(URL initial) throws Exception {
        URL url = initial;
        for (int redirects = 0; redirects <= 4; redirects++) {
            if (!allowedUrl(url)) throw new UpdateFailure("Destino de atualização não permitido.");
            HttpsURLConnection connection = (HttpsURLConnection) url.openConnection();
            connection.setInstanceFollowRedirects(false);
            connection.setConnectTimeout(15000);
            connection.setReadTimeout(30000);
            connection.setRequestProperty("User-Agent", "Elysia-Android/2.2");
            connection.setRequestProperty("Cache-Control", "no-cache");
            int code = connection.getResponseCode();
            if (code == 301 || code == 302 || code == 303 || code == 307 || code == 308) {
                String location = connection.getHeaderField("Location");
                connection.disconnect();
                if (location == null) throw new UpdateFailure("Redirecionamento de atualização inválido.");
                url = new URL(url, location);
            } else { return connection; }
        }
        throw new UpdateFailure("A publicação redirecionou a conexão muitas vezes.");
    }

    private static void requireSuccess(int status) throws UpdateFailure {
        if (status == 403 || status == 429) throw new UpdateFailure("O GitHub limitou as consultas. Aguarde e tente novamente.");
        if (status != 200) throw new UpdateFailure("A atualização não está disponível no GitHub. Tente novamente mais tarde.");
    }

    private static byte[] readBounded(InputStream input, int limit) throws Exception {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        byte[] buffer = new byte[4096];
        int count;
        while ((count = input.read(buffer)) != -1) {
            if (bytes.size() + count > limit) throw new UpdateFailure("Os dados da atualização são grandes demais.");
            bytes.write(buffer, 0, count);
        }
        return bytes.toByteArray();
    }
}
