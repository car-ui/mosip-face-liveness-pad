"""Run checks against a prepared, compiled MOSIP desktop checkout and its runtime classpath."""
import argparse
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PIN = "935306e2fd38bff2803697468e595026b1d18cec"


def run(java_home: Path, checkout: Path, classpath_file: Path, output: Path, preview: bool):
    checkout = checkout.resolve(strict=True)
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=checkout, text=True).strip()
    if actual != PIN:
        raise SystemExit(f"Expected desktop upstream {PIN}, got {actual}")
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    suffix = ".exe" if os.name == "nt" else ""
    java = java_home / "bin" / ("java" + suffix)
    javac = java_home / "bin" / ("javac" + suffix)
    modules = ["registration-client", "registration-services", "registration-api", "registration-api-stub-impl"]
    classes = [checkout / "registration" / name / "target/classes" for name in modules]
    for path in classes:
        if not path.is_dir():
            raise SystemExit(f"Compile the prepared desktop reactor first; missing {path}")
    # This is Maven's resolved runtime classpath, not an enumeration of every cached JAR.
    dependencies = classpath_file.read_text(encoding="utf-8-sig").strip()
    if not dependencies or "\n" in dependencies:
        raise SystemExit("Classpath file must contain one resolved runtime classpath line")
    classpath = os.pathsep.join([str(output), *(str(p) for p in classes), dependencies])
    names = ["DesktopControllerRejectionCheck"]
    if preview:
        names.append("DesktopStreamLifecycleCheck")
    # An argument file avoids the Windows command-line length limit.
    def quoted(value):
        return '"' + str(value).replace("\\", "/").replace('"', '\\"') + '"'
    # Check sources have no generated annotations; ignore processors from app dependencies.
    compile_args = ["--release", "8", "-proc:none", "-cp", quoted(classpath), "-d", quoted(output)]
    compile_args += [quoted(ROOT / "integrations/native/tests" / (name + ".java")) for name in names]
    compile_args.append(quoted(ROOT / "integrations/native/tests/NativeActiveSessionCheck.java"))
    args_file = output / "javac.args"
    args_file.write_text("\n".join(compile_args) + "\n", encoding="utf-8")
    subprocess.run([str(javac), "-J-Xmx192m", "-J-XX:+UseSerialGC", "-J-XX:ReservedCodeCacheSize=32m",
                    "-J-XX:CompressedClassSpaceSize=32m", "@" + str(args_file)], check=True, timeout=120)
    reports = []
    for name in names:
        java_args = ["-Xmx128m", "-XX:+UseSerialGC", quoted("-Djava.io.tmpdir=" + str(output)),
                     "-cp", quoted(classpath), name]
        if name == "DesktopControllerRejectionCheck":
            java_args.append(quoted(ROOT / "tests/sample_images/astronaut.png"))
        args_file = output / (name + ".args")
        args_file.write_text("\n".join(java_args) + "\n", encoding="utf-8")
        result = subprocess.run([str(java), "@" + str(args_file)], capture_output=True,
                                text=True, timeout=120)
        log = output / (name + ".log")
        log.write_text(result.stdout + result.stderr, encoding="utf-8")
        if result.returncode:
            raise SystemExit(f"{name} failed; inspect {log}")
        lines = [s for s in result.stdout.splitlines() if s.startswith(("PASS ", "Evidence scope:"))]
        print("\n".join(lines))
        reports.append({"check": name, "status": "PASS", "results": lines, "log": log.name})
    (output / "report.json").write_text(json.dumps({"upstream_commit": PIN, "checks": reports}, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--java-home", type=Path, required=True, help="Java 11 JDK")
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--classpath-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "output/local/desktop-check")
    parser.add_argument("--preview", action="store_true", help="Also start JavaFX without showing a window; requires a display")
    args = parser.parse_args()
    run(args.java_home, args.checkout, args.classpath_file, args.output, args.preview)
