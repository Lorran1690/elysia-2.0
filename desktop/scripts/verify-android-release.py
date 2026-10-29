"""Check a signed production APK against its public update descriptor.

Reads actual package identity with Android aapt2 and verifies the signature with
apksigner. No private signing material is needed or read by this verification.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

PACKAGE = "org.elysia.mobile"
APK_NAME = "Elysia-Android.apk"
APK_URL = "https://raw.githubusercontent.com/Lorran1690/elysia-2.0/refs/heads/feature/media-creation/artifacts/android/" + APK_NAME
MAX_APK = 100 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def run(command):
    result = subprocess.run(command, text=True, capture_output=True, timeout=120)
    require(result.returncode == 0, "Android package verification tool failed: " + Path(command[0]).name)
    return result.stdout


def verify(apk, manifest, aapt2, apksigner):
    require(manifest.stat().st_size <= 65536, "Update descriptor exceeds the size limit.")
    descriptor = json.loads(manifest.read_text(encoding="utf-8"))
    require(isinstance(descriptor, dict) and descriptor.get("format") == "elysia-android-update-v1", "Invalid update descriptor format.")
    payload = descriptor.get("apk")
    require(isinstance(payload, dict), "Missing APK identity in the descriptor.")
    version, build, source, certificate = (descriptor.get(k) for k in ("version", "build", "source_sha", "certificate_sha256"))
    require(isinstance(version, str) and re.fullmatch(r"(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})\.(0|[1-9][0-9]{0,8})", version), "Invalid Android version name.")
    require(type(build) is int and 0 < build < 2147483647, "Invalid Android version code.")
    require(isinstance(source, str) and re.fullmatch(r"[a-f0-9]{40}", source), "Invalid source commit.")
    require(isinstance(certificate, str) and re.fullmatch(r"[a-f0-9]{64}", certificate), "Missing public certificate fingerprint.")
    require(payload.get("name") == APK_NAME and payload.get("url") == APK_URL, "Update descriptor points to a foreign APK.")
    require(type(payload.get("bytes")) is int and 0 < payload["bytes"] <= MAX_APK, "Invalid declared APK size.")
    require(apk.is_file() and apk.stat().st_size == payload["bytes"], "APK size does not match the descriptor.")
    require(isinstance(payload.get("sha256"), str) and re.fullmatch(r"[a-f0-9]{64}", payload["sha256"]), "Invalid declared APK checksum.")
    with apk.open("rb") as stream:
        actual_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    require(actual_hash == payload["sha256"], "APK SHA-256 does not match the descriptor.")

    badging = run([str(aapt2.resolve()), "dump", "badging", str(apk.resolve())])
    package = re.search(r"^package:\s+name='([^']+)'\s+versionCode='([0-9]+)'\s+versionName='([^']*)'", badging, re.MULTILINE)
    require(package is not None, "aapt2 did not return an APK package identity.")
    require(package.group(1) == PACKAGE, "The signed APK has a foreign application ID.")
    require(int(package.group(2)) == build, "Actual APK version code differs from the update descriptor.")
    require(package.group(3) == version, "Actual APK version name differs from the update descriptor.")
    require(not re.search(r"^application-debuggable(?:\s|$)", badging, re.MULTILINE), "A debuggable APK cannot be published as production.")
    require(not re.search(r"^application-testOnly(?:\s|$)", badging, re.MULTILINE), "A test-only APK cannot be published as production.")

    verifier = ["java", "-jar", str(apksigner.resolve())] if apksigner.suffix == ".jar" else [str(apksigner.resolve())]
    signatures = run([*verifier, "verify", "--verbose", "--print-certs", str(apk.resolve())])
    signers = re.findall(r"^Signer #([0-9]+) certificate SHA-256 digest: ([a-fA-F0-9]{64})\s*$", signatures, re.MULTILINE)
    require(len(signers) == 1 and signers[0][1].lower() == certificate, "Actual APK signer differs from the public project fingerprint.")

    return {
        "passed": True,
        "actual_binary_manifest_checked": True,
        "application_id": package.group(1),
        "version_name": package.group(3),
        "version_code": int(package.group(2)),
        "descriptor_source_commit": source,
        "apk_bytes": apk.stat().st_size,
        "apk_sha256": actual_hash,
        "certificate_sha256": signers[0][1].lower(),
        "signature_verified_by_android_apksigner": True,
        "descriptor_matches_apk_identity_size_hash_and_signer": True,
        "production_apk_not_debuggable": True,
        "private_signing_material_read": False,
        "apk_executed_by_this_check": False,
        "embedded_source_commit_evaluated": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", type=Path, default=Path("artifacts/android/Elysia-Android.apk"))
    parser.add_argument("--manifest", type=Path, default=Path("artifacts/android/latest.json"))
    parser.add_argument("--aapt2", type=Path, required=True)
    parser.add_argument("--apksigner", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("reports/android-release/package-verification.json"))
    args = parser.parse_args()
    report = verify(args.apk, args.manifest, args.aapt2, args.apksigner)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
