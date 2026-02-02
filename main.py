import argparse
import sys
import time
from datetime import datetime

def run_step(step_num, step_name, step_func, **kwargs):
    """Run a pipeline step with timing and error handling."""
    print(f"\n{'='*60}")
    print(f"STEP {step_num}: {step_name}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print('='*60)

    start = time.time()
    try:
        step_func(**kwargs)
        elapsed = time.time() - start
        print(f"✓ Step {step_num} completed in {elapsed:.1f}s")
        return True
    except Exception as e:
        elapsed = time.time() - start
        print(f"✗ Step {step_num} failed after {elapsed:.1f}s: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Run dissertation pipeline')
    parser.add_argument('--skip-extraction', action='store_true',
                        help='Skip Step 2, use existing extracted data')
    parser.add_argument('--skip-existing', action='store_true',
                        help='Skip already extracted videos in Step 2')
    parser.add_argument('--steps', nargs='+', type=int,
                        help='Run specific steps only (e.g., --steps 3 6 7)')
    parser.add_argument('--archive', action='store_true',
                        help='Archive previous output before running')
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print("DISSERTATION PIPELINE")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print('='*60)

    # Import step modules
    from scripts import step2_batch_extract
    from scripts import step3_sensitivity_analysis
    from scripts import step4_comments_analysis
    from scripts import step5_algospeak_detection
    from scripts import step6_generate_report
    from scripts import step7_visualizations

    steps_to_run = args.steps or [2, 3, 4, 5, 6, 7]
    results = {}

    # Handle archive if requested
    if args.archive:
        import shutil
        from pathlib import Path
        output_dir = Path('data/output')
        if output_dir.exists():
            archive_name = f"output_archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            archive_path = Path('data') / archive_name
            shutil.move(str(output_dir), str(archive_path))
            print(f"Archived previous output to: {archive_path}")
            output_dir.mkdir(parents=True, exist_ok=True)

    # Step 2: Batch extraction
    if 2 in steps_to_run and not args.skip_extraction:
        # Modify sys.argv for step2's argparse
        original_argv = sys.argv
        sys.argv = ['step2_batch_extract.py']
        if args.skip_existing:
            sys.argv.append('--skip-existing')
        results[2] = run_step(2, "Batch Extract", step2_batch_extract.main)
        sys.argv = original_argv

    # Steps 3, 4, 5: Analysis (independent, run sequentially)
    if 3 in steps_to_run:
        results[3] = run_step(3, "Sensitivity Analysis", step3_sensitivity_analysis.main)
    if 4 in steps_to_run:
        results[4] = run_step(4, "Comments Perception", step4_comments_analysis.main)
    if 5 in steps_to_run:
        results[5] = run_step(5, "Algospeak Detection", step5_algospeak_detection.main)

    # Step 6: Generate report
    if 6 in steps_to_run:
        results[6] = run_step(6, "Generate Report", step6_generate_report.main)

    # Step 7: Visualizations
    if 7 in steps_to_run:
        results[7] = run_step(7, "Generate Visualizations", step7_visualizations.main)

    # Summary
    print(f"\n{'='*60}")
    print("PIPELINE COMPLETE")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print('='*60)

    step_names = {
        2: "Batch Extract",
        3: "Sensitivity Analysis",
        4: "Comments Perception",
        5: "Algospeak Detection",
        6: "Generate Report",
        7: "Visualizations"
    }

    for step, success in sorted(results.items()):
        status = "✓" if success else "✗"
        print(f"  Step {step} ({step_names[step]}): {status}")

    # Return exit code based on results
    if all(results.values()):
        print("\nAll steps completed successfully!")
        return 0
    else:
        failed = [s for s, ok in results.items() if not ok]
        print(f"\nSome steps failed: {failed}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
