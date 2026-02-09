"""
Main Pipeline Orchestrator

Runs the full dissertation analysis pipeline for YouTube self-censorship research.

This script coordinates all 7 steps of the analysis:
- Step 2: Extract video data (metadata, transcripts, comments) via APIs
- Step 3: Analyse transcript sensitivity (RQ1)
- Step 4: Analyse comment perception keywords (RQ2)
- Step 5: Detect algospeak in transcripts and comments (RQ3)
- Step 6: Generate combined Excel report
- Step 7: Generate visualisation charts
"""
import argparse
import sys
import time
from datetime import datetime

# Step name mapping for display
STEP_NAMES = {
    2: "Batch Extract",
    3: "Sensitivity Analysis",
    4: "Comments Perception",
    5: "Algospeak Detection",
    6: "Generate Report",
    7: "Visualizations"
}


def run_step(step_num: int, step_name: str, step_func, **kwargs) -> bool:
    
    # Execute a single pipeline step with timing and error handling.

    # Args:
    #     step_num: Step number (2-7)
    #     step_name: Human-readable step name
    #     step_func: The step's main() function to call
    #     **kwargs: Arguments to pass to the step function

    # Returns:
    #     True if step succeeded, False if it failed
    
    print(f"\n{'='*60}")
    print(f"STEP {step_num}: {step_name}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print('='*60)

    start = time.time()
    try:
        step_func(**kwargs)
        elapsed = time.time() - start
        print(f"Step {step_num} completed in {elapsed:.1f}s")
        return True
    except Exception as e:
        elapsed = time.time() - start
        print(f"Step {step_num} failed after {elapsed:.1f}s: {e}")
        return False


def archive_previous_output():
    
    # Move existing output folder to timestamped archive.

    # Creates data/output_archive_YYYYMMDD_HHMMSS/ containing previous results.
    
    import shutil
    from pathlib import Path

    output_dir = Path('data/output')
    if not output_dir.exists():
        return

    archive_name = f"output_archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    archive_path = Path('data') / archive_name
    shutil.move(str(output_dir), str(archive_path))
    print(f"Archived previous output to: {archive_path}")
    output_dir.mkdir(parents=True, exist_ok=True)


def main():
    # Main entry point - parse arguments and run selected pipeline steps."""

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Run dissertation analysis pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    Run full pipeline
  python main.py --skip-extraction  Use existing extracted data
  python main.py --steps 3 6 7      Run only steps 3, 6, and 7
        """
    )
    parser.add_argument('--skip-extraction', action='store_true',
                        help='Skip Step 2 (extraction), use existing data')
    parser.add_argument('--skip-existing', action='store_true',
                        help='In Step 2, skip videos already extracted')
    parser.add_argument('--steps', nargs='+', type=int, metavar='N',
                        help='Run specific steps only (e.g., --steps 3 6 7)')
    parser.add_argument('--archive', action='store_true',
                        help='Archive previous output before running')
    args = parser.parse_args()

    # Print header
    print(f"\n{'='*60}")
    print("DISSERTATION PIPELINE")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print('='*60)

    # Import step modules (deferred to avoid import errors if not all deps installed)
    from scripts import step2_batch_extract
    from scripts import step3_sensitivity_analysis
    from scripts import step4_comments_analysis
    from scripts import step5_algospeak_detection
    from scripts import step6_generate_report
    from scripts import step7_visualizations

    # Determine which steps to run
    steps_to_run = args.steps or [2, 3, 4, 5, 6, 7]
    results = {}

    # Archive previous output if requested
    if args.archive:
        archive_previous_output()

    # Step 2: Batch extraction (skippable)
    if 2 in steps_to_run and not args.skip_extraction:
        # Temporarily modify sys.argv for step2's argparse
        original_argv = sys.argv
        sys.argv = ['step2_batch_extract.py']
        if args.skip_existing:
            sys.argv.append('--skip-existing')
        results[2] = run_step(2, "Batch Extract", step2_batch_extract.main)
        sys.argv = original_argv

    # Steps 3-5: Analysis (run sequentially)
    if 3 in steps_to_run:
        results[3] = run_step(3, "Sensitivity Analysis", step3_sensitivity_analysis.main)
    if 4 in steps_to_run:
        results[4] = run_step(4, "Comments Perception", step4_comments_analysis.main)
    if 5 in steps_to_run:
        results[5] = run_step(5, "Algospeak Detection", step5_algospeak_detection.main)

    # Step 6: Generate report
    if 6 in steps_to_run:
        results[6] = run_step(6, "Generate Report", step6_generate_report.main)

    # Step 7: Generate visualizations
    if 7 in steps_to_run:
        results[7] = run_step(7, "Generate Visualizations", step7_visualizations.main)

    # Print summary
    print(f"\n{'='*60}")
    print("PIPELINE COMPLETE")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print('='*60)

    for step, success in sorted(results.items()):
        status = "OK" if success else "FAILED"
        print(f"  Step {step} ({STEP_NAMES[step]}): {status}")

    # Return appropriate exit code
    if all(results.values()):
        print("\nAll steps completed successfully!")
        return 0
    else:
        failed = [s for s, ok in results.items() if not ok]
        print(f"\nSome steps failed: {failed}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
