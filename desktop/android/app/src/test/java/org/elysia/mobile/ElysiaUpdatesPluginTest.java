package org.elysia.mobile;

import static org.junit.Assert.*;
import java.io.File;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.Set;
import org.junit.Test;

public class ElysiaUpdatesPluginTest {
    @Test
    public void updateHostsNeverAllowHttpCredentialsOrLookalikes() throws Exception {
        assertTrue(ElysiaUpdatesPlugin.allowedUrl(new URL(ElysiaUpdatesPlugin.APK_URL)));
        assertTrue(ElysiaUpdatesPlugin.allowedUrl(new URL("https://release-assets.githubusercontent.com/asset?signature=test")));
        for (String value : new String[] {
            "http://raw.githubusercontent.com/file", "https://github.com.attacker.invalid/file",
            "https://raw.githubusercontent.com:444/file", "https://user:pass@github.com/file",
            "https://127.0.0.1/file", "https://github.com/file#fragment"
        }) assertFalse(value, ElysiaUpdatesPlugin.allowedUrl(new URL(value)));
    }

    @Test
    public void buildsMustAdvanceAndVersionsCannotDowngrade() {
        assertTrue(ElysiaUpdatesPlugin.newer("2.2.0", 11, "2.2.0", 10));
        assertTrue(ElysiaUpdatesPlugin.newer("2.3.0", 11, "2.2.0", 10));
        assertFalse(ElysiaUpdatesPlugin.newer("2.2.0", 10, "2.2.0", 10));
        assertFalse(ElysiaUpdatesPlugin.newer("2.3.0", 9, "2.2.0", 10));
        assertFalse(ElysiaUpdatesPlugin.newer("2.1.9", 11, "2.2.0", 10));
        assertFalse(ElysiaUpdatesPlugin.newer("untrusted", 11, "2.2.0", 10));
        assertFalse(ElysiaUpdatesPlugin.newer("02.2.0", 11, "2.2.0", 10));
    }

    @Test
    public void missingForeignOrPartialSignerSetsFailClosed() {
        assertTrue(ElysiaUpdatesPlugin.sameSigners(Set.of("signer-a", "signer-b"), Set.of("signer-b", "signer-a")));
        assertFalse(ElysiaUpdatesPlugin.sameSigners(Set.of(), Set.of()));
        assertFalse(ElysiaUpdatesPlugin.sameSigners(Set.of("signer-a"), Set.of("signer-b")));
        assertFalse(ElysiaUpdatesPlugin.sameSigners(Set.of("signer-a", "signer-b"), Set.of("signer-a")));
    }

    @Test
    public void sameLengthCorruptionAndTruncationAreRejected() throws Exception {
        byte[] bytes = "fixture bytes, never an Android package".getBytes(StandardCharsets.UTF_8);
        String digest = ElysiaUpdatesPlugin.hex(MessageDigest.getInstance("SHA-256").digest(bytes));
        ElysiaUpdatesPlugin.Candidate candidate = new ElysiaUpdatesPlugin.Candidate("2.2.0", 10, "a".repeat(40), bytes.length, digest);
        File file = File.createTempFile("elysia-update-check-", ".apk");
        try {
            Files.write(file.toPath(), bytes);
            ElysiaUpdatesPlugin.verifyHash(file, candidate);
            bytes[0] ^= 1;
            Files.write(file.toPath(), bytes);
            assertThrows(Exception.class, () -> ElysiaUpdatesPlugin.verifyHash(file, candidate));
            Files.write(file.toPath(), new byte[1]);
            assertThrows(Exception.class, () -> ElysiaUpdatesPlugin.verifyHash(file, candidate));
        } finally { file.delete(); }
    }
}
