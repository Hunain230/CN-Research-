"""One-time archive of v1 generator quality pilot before authoritative v2."""
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
PILOT = HERE / "artifacts/pilot_v1"


def main():
    assert HERE.is_absolute()
    PILOT.mkdir(parents=True, exist_ok=False)
    targets = [HERE / "dataset"]
    targets.extend((HERE / "artifacts").glob("development_*"))
    targets.append(HERE / "artifacts/generator_validation.json")
    targets.extend(HERE / name for name in ("DEVELOPMENT_RESULTS.csv", "CANDIDATE_COMPARISON.csv", "QUEUE_LEVEL_AUDIT.csv"))
    for source in targets:
        resolved = source.resolve()
        assert resolved.is_relative_to(HERE) and resolved != HERE
        if source.exists(): shutil.move(str(source), str(PILOT / source.name))
    print(f"Archived {len(targets)} pilot paths")


if __name__ == "__main__": main()
