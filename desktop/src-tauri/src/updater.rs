//! Explicit, per-user updates from this project's verified GitHub native releases.
//! No frontend URL/path is accepted and no update runs without an install command.
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{
    fs::{self, File, OpenOptions},
    io::{Read, Write},
    path::{Path, PathBuf},
    sync::Mutex,
    time::{Duration, Instant},
};
use tauri::{Emitter, Manager};

const REPOSITORY: &str = "Lorran1690/elysia-2.0";
const RELEASES_API: &str =
    "https://api.github.com/repos/Lorran1690/elysia-2.0/releases?per_page=30";
const INSTALLER: &str = "Elysia-Setup-x64.exe";
const MANIFEST: &str = "elysia-update.json";
const MAX_INSTALLER: u64 = 1024 * 1024 * 1024;

#[derive(Clone, Deserialize, Serialize)]
pub struct Candidate {
    pub version: String,
    pub build: u64,
    pub source_sha: String,
    pub tag: String,
    pub bytes: u64,
    pub sha256: String,
    pub release_url: String,
}
#[derive(Clone, Deserialize)]
struct Manifest {
    format: String,
    repository: String,
    version: String,
    build: u64,
    source_sha: String,
    tag: String,
    installer: Installer,
}
#[derive(Clone, Deserialize)]
struct Installer {
    name: String,
    url: String,
    bytes: u64,
    sha256: String,
}
#[derive(Deserialize)]
struct Release {
    tag_name: String,
    draft: bool,
    assets: Vec<Asset>,
}
#[derive(Deserialize)]
struct Asset {
    name: String,
    browser_download_url: String,
    size: u64,
    digest: Option<String>,
}
#[derive(Clone)]
struct Verified {
    candidate: Candidate,
    path: PathBuf,
}
#[derive(Default)]
struct Cache {
    candidate: Option<Candidate>,
    verified: Option<Verified>,
    busy: bool,
}
#[derive(Default)]
pub struct Updater {
    cache: Mutex<Cache>,
}
#[derive(Serialize)]
pub struct Status {
    supported: bool,
    installed: bool,
    current_version: &'static str,
    current_build: u64,
    current_source: &'static str,
    status: &'static str,
    candidate: Option<Candidate>,
}
#[derive(Clone, Serialize)]
struct Progress {
    stage: &'static str,
    downloaded: u64,
    total: u64,
}
#[derive(Serialize)]
pub struct Downloaded {
    verified: bool,
    version: String,
    build: u64,
    bytes: u64,
    sha256: String,
}

fn current_build() -> u64 {
    env!("ELYSIA_BUILD_NUMBER").parse().unwrap_or(0)
}
fn current_source() -> &'static str {
    env!("ELYSIA_BUILD_SHA")
}
fn install_directory() -> Option<PathBuf> {
    if !cfg!(windows) {
        return None;
    }
    let dir = std::env::current_exe().ok()?.parent()?.to_path_buf();
    // Portable archives are deliberately not converted into registered installations.
    dir.join("unins000.exe").is_file().then_some(dir)
}
fn status(candidate: Option<Candidate>) -> Status {
    let supported = cfg!(windows);
    Status {
        supported,
        installed: install_directory().is_some(),
        current_version: env!("CARGO_PKG_VERSION"),
        current_build: current_build(),
        current_source: current_source(),
        status: if !supported {
            "unsupported"
        } else if candidate.is_some() {
            "available"
        } else {
            "up-to-date"
        },
        candidate,
    }
}
fn valid_hex(value: &str, count: usize) -> bool {
    value.len() == count
        && value
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}
fn release_asset_url(tag: &str, name: &str) -> String {
    format!("https://github.com/{REPOSITORY}/releases/download/{tag}/{name}")
}
fn allowed_redirect(url: &reqwest::Url) -> bool {
    url.scheme() == "https"
        && url.port_or_known_default() == Some(443)
        && url.username().is_empty()
        && url.password().is_none()
        && matches!(
            url.host_str(),
            Some(
                "github.com"
                    | "release-assets.githubusercontent.com"
                    | "objects.githubusercontent.com"
            )
        )
}
fn client(timeout: u64) -> Result<reqwest::Client, String> {
    reqwest::Client::builder()
        .https_only(true)
        .connect_timeout(Duration::from_secs(15))
        .timeout(Duration::from_secs(timeout))
        .user_agent(concat!("Elysia-Desktop/", env!("CARGO_PKG_VERSION")))
        .redirect(reqwest::redirect::Policy::custom(|attempt| {
            if attempt.previous().len() >= 4 || !allowed_redirect(attempt.url()) {
                attempt.error("Destino de atualização não permitido")
            } else {
                attempt.follow()
            }
        }))
        .build()
        .map_err(|_| "Não foi possível preparar a conexão segura.".into())
}
async fn fetch_small(client: &reqwest::Client, url: &str, limit: usize) -> Result<Vec<u8>, String> {
    let mut response = client
        .get(url)
        .header("Accept", "application/vnd.github+json")
        .header("X-GitHub-Api-Version", "2022-11-28")
        .send()
        .await
        .map_err(|_| {
            "Não foi possível consultar o GitHub. Verifique sua conexão e tente novamente."
        })?;
    if !response.status().is_success() {
        return Err(
            if response.status().as_u16() == 403 || response.status().as_u16() == 429 {
                "O GitHub limitou as consultas. Aguarde alguns minutos e tente novamente."
            } else {
                "O GitHub não disponibilizou a atualização. Tente novamente mais tarde."
            }
            .into(),
        );
    }
    if response.content_length().is_some_and(|n| n > limit as u64) {
        return Err("Metadados de atualização grandes demais.".into());
    }
    let mut bytes = Vec::new();
    while let Some(chunk) = response
        .chunk()
        .await
        .map_err(|_| "A consulta de atualização foi interrompida.")?
    {
        if bytes.len() + chunk.len() > limit {
            return Err("Metadados de atualização grandes demais.".into());
        }
        bytes.extend_from_slice(&chunk);
    }
    Ok(bytes)
}
fn validate_manifest(manifest: Manifest, release: &Release) -> Result<Candidate, String> {
    let invalid = || "A publicação não contém uma atualização íntegra da Elysia.".to_string();
    if release.draft
        || manifest.format != "elysia-native-update-v1"
        || manifest.repository != REPOSITORY
        || !valid_hex(&manifest.source_sha, 40)
        || manifest.tag != format!("native-{}", &manifest.source_sha[..12])
        || manifest.tag != release.tag_name
        || manifest.build == 0
        || semver::Version::parse(&manifest.version).is_err()
        || manifest.installer.name != INSTALLER
        || manifest.installer.url != release_asset_url(&manifest.tag, INSTALLER)
        || manifest.installer.bytes == 0
        || manifest.installer.bytes > MAX_INSTALLER
        || !valid_hex(&manifest.installer.sha256, 64)
    {
        return Err(invalid());
    }
    let assets: Vec<_> = release
        .assets
        .iter()
        .filter(|a| a.name == INSTALLER)
        .collect();
    if assets.len() != 1 {
        return Err(invalid());
    }
    let asset = assets[0];
    if asset.browser_download_url != manifest.installer.url
        || asset.size != manifest.installer.bytes
        || asset.digest.as_deref() != Some(format!("sha256:{}", manifest.installer.sha256).as_str())
    {
        return Err(invalid());
    }
    Ok(Candidate {
        version: manifest.version,
        build: manifest.build,
        source_sha: manifest.source_sha,
        tag: manifest.tag.clone(),
        bytes: manifest.installer.bytes,
        sha256: manifest.installer.sha256,
        release_url: format!(
            "https://github.com/{REPOSITORY}/releases/tag/{}",
            manifest.tag
        ),
    })
}
fn newer(candidate: &Candidate, version: &str, build: u64) -> bool {
    let (Ok(next), Ok(current)) = (
        semver::Version::parse(&candidate.version),
        semver::Version::parse(version),
    ) else {
        return false;
    };
    candidate.build > build && next >= current
}
fn verify_file(path: &Path, candidate: &Candidate) -> Result<(), String> {
    let mut file = File::open(path)
        .map_err(|_| "O instalador baixado não está disponível. Baixe a atualização novamente.")?;
    if file
        .metadata()
        .map_err(|_| "Não foi possível verificar o instalador.")?
        .len()
        != candidate.bytes
    {
        return Err("O tamanho do instalador não confere. Baixe a atualização novamente.".into());
    }
    let mut hash = Sha256::new();
    let mut buffer = [0_u8; 65536];
    loop {
        let n = file
            .read(&mut buffer)
            .map_err(|_| "Não foi possível verificar o instalador.")?;
        if n == 0 {
            break;
        }
        hash.update(&buffer[..n]);
    }
    if format!("{:x}", hash.finalize()) != candidate.sha256 {
        return Err("A integridade do instalador falhou. Nenhum arquivo foi executado. Baixe a atualização novamente.".into());
    }
    Ok(())
}
#[tauri::command]
pub fn updater_info(state: tauri::State<Updater>) -> Result<Status, String> {
    Ok(status(
        state
            .cache
            .lock()
            .map_err(|_| "Atualizador indisponível")?
            .candidate
            .clone(),
    ))
}
#[tauri::command]
pub async fn check_update(state: tauri::State<'_, Updater>) -> Result<Status, String> {
    if !cfg!(windows) {
        return Ok(status(None));
    }
    {
        let mut cache = state.cache.lock().map_err(|_| "Atualizador indisponível")?;
        if cache.busy {
            return Err("Uma atualização já está em andamento.".into());
        }
        cache.busy = true;
    }
    let result = async {
        let client = client(45)?;
        let releases: Vec<Release> =
            serde_json::from_slice(&fetch_small(&client, RELEASES_API, 4 * 1024 * 1024).await?)
                .map_err(|_| "Resposta de atualização inválida.")?;
        let mut candidates = Vec::new();
        // Release publication is newest-first. Old releases without this manifest are skipped.
        // Inspect at most five native manifests to keep checks and API usage bounded.
        for release in releases
            .iter()
            .filter(|r| !r.draft && r.tag_name.starts_with("native-"))
            .filter(|r| r.assets.iter().any(|a| a.name == MANIFEST))
            .take(5)
        {
            if release.assets.iter().filter(|a| a.name == MANIFEST).count() != 1 {
                continue;
            }
            let asset = release.assets.iter().find(|a| a.name == MANIFEST).unwrap();
            if asset.browser_download_url != release_asset_url(&release.tag_name, MANIFEST)
                || asset.size == 0
                || asset.size > 64 * 1024
            {
                continue;
            }
            let raw = fetch_small(&client, &asset.browser_download_url, 64 * 1024).await?;
            let manifest: Manifest = serde_json::from_slice(&raw)
                .map_err(|_| "O manifesto de atualização é inválido.")?;
            let candidate = validate_manifest(manifest, release)?;
            if newer(&candidate, env!("CARGO_PKG_VERSION"), current_build()) {
                candidates.push(candidate);
            }
        }
        Ok::<_, String>(candidates.into_iter().max_by_key(|c| c.build))
    }
    .await;
    let mut cache = state.cache.lock().map_err(|_| "Atualizador indisponível")?;
    cache.busy = false;
    let candidate = result?;
    // Reuse a verified download of exactly the same release, never an older candidate.
    if cache.verified.as_ref().is_some_and(|v| {
        candidate
            .as_ref()
            .is_none_or(|c| c.sha256 != v.candidate.sha256 || c.build != v.candidate.build)
    }) {
        cache.verified = None;
    }
    cache.candidate = candidate.clone();
    Ok(status(candidate))
}
#[tauri::command]
pub async fn download_update(
    app: tauri::AppHandle,
    state: tauri::State<'_, Updater>,
) -> Result<Downloaded, String> {
    if install_directory().is_none() {
        return Err("A atualização interna está disponível na edição instalada para Windows. A edição portátil deve ser substituída manualmente.".into());
    }
    let candidate = {
        let mut cache = state.cache.lock().map_err(|_| "Atualizador indisponível")?;
        if cache.busy {
            return Err("Uma atualização já está em andamento.".into());
        }
        let candidate = cache
            .candidate
            .clone()
            .ok_or("Verifique as atualizações primeiro.")?;
        cache.busy = true;
        candidate
    };
    let folder = app.state::<crate::Desktop>().data.join("updates");
    let part = folder.join(format!("{}.part", uuid::Uuid::new_v4()));
    let path = folder.join(format!(
        "Elysia-Setup-{}-{}.exe",
        candidate.build,
        uuid::Uuid::new_v4()
    ));
    let result = async {
        fs::create_dir_all(&folder)
            .map_err(|_| "Não foi possível criar a pasta privada de atualizações.")?;
        let client = client(900)?;
        let mut response = client
            .get(release_asset_url(&candidate.tag, INSTALLER))
            .send()
            .await
            .map_err(|_| "Não foi possível baixar a atualização. Verifique sua conexão.")?;
        if !response.status().is_success()
            || response
                .content_length()
                .is_some_and(|n| n != candidate.bytes)
        {
            return Err("O download do instalador não corresponde à publicação verificada.".into());
        }
        let mut file = OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(&part)
            .map_err(|_| "Não foi possível gravar o instalador. Verifique o espaço em disco.")?;
        let mut downloaded = 0_u64;
        let mut hash = Sha256::new();
        let mut tick = Instant::now();
        let _ = app.emit(
            "elysia-update-progress",
            Progress {
                stage: "downloading",
                downloaded,
                total: candidate.bytes,
            },
        );
        while let Some(chunk) = response
            .chunk()
            .await
            .map_err(|_| "O download foi interrompido. Tente novamente.")?
        {
            downloaded += chunk.len() as u64;
            if downloaded > candidate.bytes || downloaded > MAX_INSTALLER {
                return Err("O instalador recebido é maior que a publicação verificada.".into());
            }
            file.write_all(&chunk).map_err(|_| {
                "Não foi possível gravar a atualização. Verifique o espaço em disco."
            })?;
            hash.update(&chunk);
            if tick.elapsed() >= Duration::from_millis(150) {
                let _ = app.emit(
                    "elysia-update-progress",
                    Progress {
                        stage: "downloading",
                        downloaded,
                        total: candidate.bytes,
                    },
                );
                tick = Instant::now();
            }
        }
        file.sync_all()
            .map_err(|_| "Não foi possível concluir a gravação da atualização.")?;
        drop(file);
        if downloaded != candidate.bytes || format!("{:x}", hash.finalize()) != candidate.sha256 {
            return Err(
                "A integridade do download falhou. Nenhum instalador foi executado.".into(),
            );
        }
        fs::rename(&part, &path)
            .map_err(|_| "Não foi possível preparar o instalador verificado.")?;
        let _ = app.emit(
            "elysia-update-progress",
            Progress {
                stage: "verified",
                downloaded,
                total: candidate.bytes,
            },
        );
        Ok::<_, String>(Verified {
            candidate: candidate.clone(),
            path: path.clone(),
        })
    }
    .await;
    let mut cache = state.cache.lock().map_err(|_| "Atualizador indisponível")?;
    cache.busy = false;
    match result {
        Ok(verified) => {
            if let Some(previous) = cache.verified.replace(verified) {
                let _ = fs::remove_file(previous.path);
            }
            Ok(Downloaded {
                verified: true,
                version: candidate.version,
                build: candidate.build,
                bytes: candidate.bytes,
                sha256: candidate.sha256,
            })
        }
        Err(error) => {
            let _ = fs::remove_file(part);
            let _ = fs::remove_file(path);
            Err(error)
        }
    }
}
#[tauri::command]
pub async fn install_update(
    app: tauri::AppHandle,
    state: tauri::State<'_, Updater>,
) -> Result<(), String> {
    let directory = install_directory()
        .ok_or("Use a edição instalada da Elysia para atualizar pelo aplicativo.")?;
    let verified = {
        let mut cache = state.cache.lock().map_err(|_| "Atualizador indisponível")?;
        if cache.busy {
            return Err("Uma atualização já está em andamento.".into());
        }
        let verified = cache
            .verified
            .clone()
            .ok_or("Baixe e verifique a atualização primeiro.")?;
        if cache.candidate.as_ref().is_none_or(|c| {
            c.sha256 != verified.candidate.sha256 || c.build != verified.candidate.build
        }) {
            return Err("Verifique e baixe a atualização novamente.".into());
        }
        cache.busy = true;
        verified
    };
    let result = tauri::async_runtime::spawn_blocking(move || {
        verify_file(&verified.path,&verified.candidate)?;
        #[cfg(windows)]
        { std::process::Command::new(&verified.path).arg("/CURRENTUSER").arg("/NORESTART").arg("/SP-").arg(format!("/DIR={}",directory.to_string_lossy())).spawn().map_err(|_| "Não foi possível abrir o instalador. Seus dados e a versão atual foram mantidos.")?; Ok::<_,String>(()) }
        #[cfg(not(windows))]
        { let _ = directory; Err::<(),String>("Atualização disponível somente no Windows.".into()) }
    }).await;
    state
        .cache
        .lock()
        .map_err(|_| "Atualizador indisponível")?
        .busy = false;
    result.map_err(|_| "Não foi possível preparar a instalação.")??;
    // Normal Exit events dispose the owned Python core before Inno replaces its files.
    app.exit(0);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    fn fixtures() -> (Manifest, Release) {
        let sha = "a".repeat(40);
        let tag = format!("native-{}", &sha[..12]);
        let digest = "b".repeat(64);
        let url = release_asset_url(&tag, INSTALLER);
        (
            Manifest {
                format: "elysia-native-update-v1".into(),
                repository: REPOSITORY.into(),
                version: "2.2.0".into(),
                build: 100,
                source_sha: sha,
                tag: tag.clone(),
                installer: Installer {
                    name: INSTALLER.into(),
                    url: url.clone(),
                    bytes: 123,
                    sha256: digest.clone(),
                },
            },
            Release {
                tag_name: tag,
                draft: false,
                assets: vec![Asset {
                    name: INSTALLER.into(),
                    browser_download_url: url,
                    size: 123,
                    digest: Some(format!("sha256:{digest}")),
                }],
            },
        )
    }
    #[test]
    fn verifies_publication_and_rejects_foreign_or_mismatched_payloads() {
        let (m, r) = fixtures();
        assert!(validate_manifest(m, &r).is_ok());
        let (mut m, r) = fixtures();
        m.installer.url = "https://attacker.invalid/Elysia-Setup-x64.exe".into();
        assert!(validate_manifest(m, &r).is_err());
        let (m, mut r) = fixtures();
        r.assets[0].digest = Some(format!("sha256:{}", "c".repeat(64)));
        assert!(validate_manifest(m, &r).is_err());
        let (mut m, r) = fixtures();
        m.source_sha = "x".repeat(40);
        assert!(validate_manifest(m, &r).is_err());
        let (mut m, r) = fixtures();
        m.installer.bytes = MAX_INSTALLER + 1;
        assert!(validate_manifest(m, &r).is_err());
        let (m, mut r) = fixtures();
        r.assets.push(Asset {
            name: INSTALLER.into(),
            browser_download_url: "".into(),
            size: 123,
            digest: None,
        });
        assert!(validate_manifest(m, &r).is_err());
    }
    #[test]
    fn monotonic_builds_with_version_downgrade_protection() {
        let (m, r) = fixtures();
        let mut c = validate_manifest(m, &r).unwrap();
        assert!(newer(&c, "2.2.0", 99));
        assert!(!newer(&c, "2.2.0", 100));
        assert!(!newer(&c, "2.2.0", 101));
        assert!(!newer(&c, "2.3.0", 99));
        c.version = "invalid".into();
        assert!(!newer(&c, "2.2.0", 99));
    }
    #[test]
    fn redirects_never_downgrade_or_leave_release_hosts() {
        assert!(allowed_redirect(
            &"https://release-assets.githubusercontent.com/x?sig=public"
                .parse()
                .unwrap()
        ));
        for u in [
            "http://github.com/x",
            "https://github.com.attacker.invalid/x",
            "https://github.com:8443/x",
            "https://user:secret@github.com/x",
            "https://127.0.0.1/x",
        ] {
            assert!(!allowed_redirect(&u.parse().unwrap()));
        }
    }
    #[test]
    fn rehash_rejects_corruption_and_truncation_before_execution() {
        let (m, r) = fixtures();
        let mut c = validate_manifest(m, &r).unwrap();
        let bytes = b"fixture installer bytes, never executable";
        c.bytes = bytes.len() as u64;
        c.sha256 = format!("{:x}", Sha256::digest(bytes));
        let path =
            std::env::temp_dir().join(format!("elysia-update-test-{}", uuid::Uuid::new_v4()));
        fs::write(&path, bytes).unwrap();
        assert!(verify_file(&path, &c).is_ok());
        let mut changed = bytes.to_vec();
        changed[0] ^= 1;
        fs::write(&path, changed).unwrap();
        assert!(verify_file(&path, &c).is_err());
        fs::write(&path, &bytes[..bytes.len() - 1]).unwrap();
        assert!(verify_file(&path, &c).is_err());
        let _ = fs::remove_file(path);
    }
}
