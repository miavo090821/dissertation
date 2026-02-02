import argparse
import sys
import time
from datetime import datetime

def run_step(step_num, step_name, step_func, **kwargs):
    # Run a pipeline step with timing and error handling.
    print(f"\n{'='*60}")
    print(f"STEP {step_num}: {step_name}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print('='*60)

    start = time.time()
    
def main():

    parser = argparse.ArgumentParser(description='Run dissertation pipeline')
    parser.add_argument('--skip-extraction', action='store_true', help='Skip Step 2, use existing extracted data')
    parser.add_argument('--skip-existing', action='store_true',
                        help='Skip already extracted videos in Step 2')
    parser.add_argument('--steps', nargs='+', type=int,
                        help='Run specific steps only (e.g., --steps 3 6 7)')
    parser.add_argument('--archive', action='store_true',
                        help='Archive previous output before running')
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print("DISSERTATION PIPELINE")
    
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

    # Step 2: Batch extraction
    if 2 in steps_to_run and not args.skip_extraction:
        # Modify sys.argv for step2's argparse
        original_argv = sys.argv
        sys.argv = ['step2_batch_extract.py']
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

    # Return exit code based on results
    if all(results.values()):
        return 0
    else:
        failed = [s for s, ok in results.items() if not ok]
        return 1

if __name__ == '__main__':
    sys.exit(main())