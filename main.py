"""
Main Pipeline Orchestrator

Runs the full dissertation analysis pipeline for YouTube self-censorship research.

Pipeline Phases:
  PHASE 1 — DATA COLLECTION
    Step 1:  Detect ads on videos (requires visible browser)
             Methods: stealth (default), dom, network-api
    Step 2:  Extract video data (metadata, transcripts, comments) via APIs

  PHASE 2 — ANALYSIS
    Step 3:  Analyse transcript sensitivity (RQ1)
    Step 3b: Cross-category analysis (sensitive words vs algospeak categories)
    Step 4:  Analyse comment perception keywords (RQ2)
    Step 5:  Detect algospeak in transcripts and comments (RQ3)

  PHASE 3 — OUTPUT
    Step 6:  Generate combined Excel report
    Step 7:  Generate visualisation charts

  PHASE 4 — SUMMARY
    Save pipeline_report.txt + print recovery commands

Scenarios:
  1. Fresh start:                    python3 main.py
  2. Resume after crash:             python3 main.py --skip-existing --continue-on-failure
  3. Ad detection failed mid-run:    python3 main.py --steps 1 --skip-existing
  4. Different detection method:     python3 main.py --steps 1 --method dom
  5. Re-run analysis only:           python3 main.py --skip-extraction
  6. Run overnight, tolerate errors: python3 main.py --continue-on-failure
"""
#1. runs the full dissertation pipeline for youtube self-censorship research
#2. phase 1 collects data (ad detection + video extraction), phase 2 does analysis (sensitivity, comments, algospeak)
#3. phase 3 generates the excel report and charts, phase 4 saves a summary report with recovery commands
#4. supports resuming after crashes with --skip-existing and --continue-on-failure flags
#5. you can run individual steps with --steps or swap ad detection methods with --method

import argparse
import os
import sys
import time
from datetime import datetime

# Step name mapping for display (string keys to support sub-steps)
STEP_NAMES = {
    '1': "Ad Detection",
    '2': "Batch Extract",
    '3': "Sensitivity Analysis",
    '3b': "Category Cross-Analysis",
    '4': "Comments Perception",
    '5': "Algospeak Detection",
    '6': "Generate Report",
    '7': "Visualizations"
}

# Default full pipeline order
ALL_STEPS = ['1', '2', '3', '3b', '4', '5', '6', '7']

# Phase groupings for display
PHASES = {
    'DATA COLLECTION': ['1', '2'],
    'ANALYSIS': ['3', '3b', '4', '5'],
    'OUTPUT': ['6', '7'],
}


def run_step(step_id: str, step_name: str, step_func, **kwargs):
    """
    Execute a single pipeline step with timing and error handling.

    Returns:
        (success, elapsed_seconds, error_message|None)
    """
    print(f"\n{'='*60}")
    print(f"STEP {step_id}: {step_name}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print('='*60)

    start = time.time()
    try:
        step_func(**kwargs)
        elapsed = time.time() - start
        print(f"Step {step_id} completed in {elapsed:.1f}s")
        return (True, elapsed, None)
    except Exception as e:
        elapsed = time.time() - start
        error_msg = f"{type(e).__name__}: {e}"
        print(f"Step {step_id} failed after {elapsed:.1f}s: {error_msg}")
        return (False, elapsed, error_msg)


def _set_step_argv(script_name, **flags):
    """Build sys.argv for a child script. Replaces scattered sys.argv manipulation."""
    sys.argv = [script_name]
    for flag, value in flags.items():
        flag_name = f'--{flag.replace("_", "-")}'
        if value is True:
            sys.argv.append(flag_name)
        elif value is not None and value is not False:
            sys.argv.extend([flag_name, str(value)])


def archive_previous_output():
    """Move existing output folder to timestamped archive."""
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


def parse_steps(step_args: list) -> list:
    """Parse step arguments, supporting both numeric and sub-step notation."""
    if not step_args:
        return list(ALL_STEPS)

    steps = []
    for s in step_args:
        s_str = str(s).lower()
        if s_str in STEP_NAMES:
            steps.append(s_str)
        else:
            try:
                int_val = str(int(s_str))
                if int_val in STEP_NAMES:
                    steps.append(int_val)
                else:
                    print(f"WARNING: Unknown step '{s}', skipping")
            except ValueError:
                print(f"WARNING: Unknown step '{s}', skipping")

    return steps


def save_pipeline_report(results, steps_to_run, skipped_steps):
    """
    Append a pipeline report to data/output/pipeline_report.txt.

    Shows timing, status, errors, and the exact recovery command for failed steps.
    """
    from pathlib import Path

    output_dir = Path('data/output')
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / 'pipeline_report.txt'

    # Find the longest step label for alignment
    labels = {}
    for step_id in ALL_STEPS:
        labels[step_id] = f"Step {step_id:<3} ({STEP_NAMES[step_id]})"
    max_label = max(len(v) for v in labels.values())

    lines = []
    lines.append(f"PIPELINE REPORT — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append('=' * 50)

    failed_steps = []

#  this is to documents what step has been done. 

    for step_id in ALL_STEPS:
        label = labels[step_id].ljust(max_label)

        if step_id in skipped_steps:
            lines.append(f"{label}  SKIPPED")
        elif step_id in results:
            ok, elapsed, err = results[step_id]
            if ok:
                lines.append(f"{label}  OK      ({elapsed:.1f}s)")
            else:
                lines.append(f"{label}  FAILED  ({elapsed:.1f}s) — {err}")
                failed_steps.append(step_id)
        elif step_id in steps_to_run:
            # Was supposed to run but didn't (pipeline stopped before reaching it)
            lines.append(f"{label}  NOT RUN")
        else:
            lines.append(f"{label}  —")

    if failed_steps:
        lines.append(f"\nFAILED STEPS: {' '.join(failed_steps)}")
        lines.append(f"RECOVERY: python3 main.py --steps {' '.join(failed_steps)}")
    else:
        lines.append("\nALL STEPS OK")

    lines.append('')  # trailing newline

    report_text = '\n'.join(lines)

    # Append to file (preserves history across runs)
    with open(report_path, 'a') as f:
        f.write(report_text + '\n')

    return report_text, failed_steps


def main():
    """Main entry point - parse arguments and run selected pipeline steps."""

    parser = argparse.ArgumentParser(
        description='Run dissertation analysis pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog= """
Scenarios:
  1. Fresh start — run everything:
     python3 main.py

  2. Resume after crash — skip completed work, tolerate failures:
     python3 main.py --skip-existing --continue-on-failure

  3. Ad detection failed mid-run — resume from where it stopped:
     python3 main.py --steps 1 --skip-existing

  4. Try a different ad detection method:
     python3 main.py --steps 1 --method dom
     python3 main.py --steps 1 --method network-api

  5. Re-run analysis only (data already collected):
     python3 main.py --skip-extraction

  6. Run overnight — don't stop on failures:
     python3 main.py --continue-on-failure

Flags:
  --continue-on-failure   Log errors and keep going instead of stopping
  --skip-existing         Skip already-processed videos (Steps 1, 2, 5)
  --skip-extraction       Skip Step 2 entirely, use existing data
  --steps N [N ...]       Run only specific steps (e.g., --steps 3 3b 6 7)
  --method {stealth,dom,network-api}  Ad detection method for Step 1
  --archive               Archive previous output before running
  --recheck-no            Re-check videos where ad_status is No
  --recheck-rounds N      Number of re-check rounds (default: 1)
        """
    )
    parser.add_argument('--skip-extraction', action='store_true',
                        help='Skip Step 2 (extraction), use existing data')
    parser.add_argument('--skip-existing', action='store_true',
                        help='Skip processed videos; in Step 1 resume unverified Nos + new; in Step 2 skip already extracted')
    parser.add_argument('--steps', nargs='+', metavar='N',
                        help='Run specific steps only (e.g., --steps 3 3b 6 7)')
    parser.add_argument('--archive', action='store_true',
                        help='Archive previous output before running')
    parser.add_argument('--recheck-no', action='store_true',
                        help='In Step 1, re-check videos where ad_status is No')
    parser.add_argument('--recheck-rounds', type=int, default=1, metavar='N',
                        help='Number of re-check rounds for --recheck-no (default: 1)')
    parser.add_argument('--method', choices=['stealth', 'dom', 'network-api'],
                        default='stealth',
                        help='Ad detection method for Step 1 (default: stealth)')
    parser.add_argument('--continue-on-failure', action='store_true',
                        help='Log errors and keep going instead of stopping the pipeline')
    args = parser.parse_args()

    # Print header
    print(f"\n{'='*60}")
    print("DISSERTATION PIPELINE")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if args.method != 'stealth':
        print(f"Ad Detection Method: {args.method}")
    if args.continue_on_failure:
        print("Mode: continue-on-failure (errors won't stop the pipeline)")
    print('='*60)

    # Import step modules (deferred to avoid import errors if not all deps installed)
    from scripts import step1_ad_detector
    from scripts import step2_batch_extract
    from scripts import step3_sensitivity_analysis
    from scripts import step3b_category_analysis
    from scripts import step4_comments_analysis
    from scripts import step5_algospeak_detection
    from scripts import step6_generate_report
    from scripts import step7_visualizations

    # determine which steps to run
    steps_to_run = parse_steps(args.steps)
    results = {}
    skipped_steps = set()

    # archive previous output if requested
    if args.archive:
        archive_previous_output()

    # track whether we should stop (only relevant without --continue-on-failure)
    pipeline_stopped = False

    # ── PHASE 1: DATA COLLECTION 

    # Step 1: Ad Detection (method-dependent) this is for selection, whether user wants to 
    # run with UI Playwright Stealth method or HTML or Network API
    #  1. is for Stealth method 
    #  2. is for HTML/DOM
    #  3. is for Network API

    if '1' in steps_to_run and not pipeline_stopped:
        if args.method == 'stealth':
            _set_step_argv('step1_ad_detector.py',
                           skip_existing=args.skip_existing or None,
                           recheck_no=args.recheck_no or None)
            results['1'] = run_step('1', "Ad Detection (Stealth/UI)", step1_ad_detector.main)

        elif args.method == 'dom':
            from scripts import step1b_dom_detector
            _set_step_argv('step1b_dom_detector.py',
                           recheck_no=args.recheck_no or None,
                           recheck_rounds=args.recheck_rounds if args.recheck_rounds > 1 else None)
            results['1'] = run_step('1', "Ad Detection (HTML/DOM)", step1b_dom_detector.main)

        elif args.method == 'network-api':
            from scripts import step1c_network_api_detector
            _set_step_argv('step1c_network_api_detector.py',
                           recheck_no=args.recheck_no or None,
                           recheck_rounds=args.recheck_rounds if args.recheck_rounds > 1 else None)
            results['1'] = run_step('1', "Ad Detection (Network API)", step1c_network_api_detector.main)

        if not results.get('1', (True,))[0] and not args.continue_on_failure:
            print(f"\nStep 1 failed. Use --continue-on-failure to keep going.")
            pipeline_stopped = True

    # Step 2: Batch extraction (skippable) 
    if '2' in steps_to_run and not pipeline_stopped:
        if args.skip_extraction:
            print("\nStep 2: Batch Extract — SKIPPED (--skip-extraction)")
            skipped_steps.add('2')
        else:
            _set_step_argv('step2_batch_extract.py',
                           skip_existing=args.skip_existing or None)
            results['2'] = run_step('2', "Batch Extract", step2_batch_extract.main)

            if not results['2'][0] and not args.continue_on_failure:
                print(f"\nStep 2 failed. Use --continue-on-failure to keep going.")
                pipeline_stopped = True

    # ── PHASE 2: ANALYSIS 

    # Step 3: Sensitivity Analysis
    if '3' in steps_to_run and not pipeline_stopped:
        _set_step_argv('step3_sensitivity_analysis.py')
        results['3'] = run_step('3', "Sensitivity Analysis", step3_sensitivity_analysis.main)

        if not results['3'][0] and not args.continue_on_failure:
            print(f"\nStep 3 failed. Use --continue-on-failure to keep going.")
            pipeline_stopped = True

    # Step 3b: Category Cross-Analysis
    if '3b' in steps_to_run and not pipeline_stopped:
        _set_step_argv('step3b_category_analysis.py')
        results['3b'] = run_step('3b', "Category Cross-Analysis", step3b_category_analysis.main)

        if not results['3b'][0] and not args.continue_on_failure:
            print(f"\nStep 3b failed. Use --continue-on-failure to keep going.")
            pipeline_stopped = True

    # Step 4: Comments Perception
    if '4' in steps_to_run and not pipeline_stopped:
        _set_step_argv('step4_comments_analysis.py')
        results['4'] = run_step('4', "Comments Perception", step4_comments_analysis.main)

        if not results['4'][0] and not args.continue_on_failure:
            print(f"\nStep 4 failed. Use --continue-on-failure to keep going.")
            pipeline_stopped = True

    # Step 5: Algospeak Detection
    if '5' in steps_to_run and not pipeline_stopped:
        _set_step_argv('step5_algospeak_detection.py',
                       skip_existing=args.skip_existing or None)
        results['5'] = run_step('5', "Algospeak Detection", step5_algospeak_detection.main)

        if not results['5'][0] and not args.continue_on_failure:
            print(f"\nStep 5 failed. Use --continue-on-failure to keep going.")
            pipeline_stopped = True

    # ── PHASE 3: OUTPUT

    # Step 6: Generate report
    if '6' in steps_to_run and not pipeline_stopped:
        _set_step_argv('step6_generate_report.py')
        results['6'] = run_step('6', "Generate Report", step6_generate_report.main)

        if not results['6'][0] and not args.continue_on_failure:
            print(f"\nStep 6 failed. Use --continue-on-failure to keep going.")
            pipeline_stopped = True

    # Step 7: Generate visualizations
    if '7' in steps_to_run and not pipeline_stopped:
        _set_step_argv('step7_visualizations.py')
        results['7'] = run_step('7', "Generate Visualizations", step7_visualizations.main)

        if not results['7'][0] and not args.continue_on_failure:
            print(f"\nStep 7 failed. Use --continue-on-failure to keep going.")
            pipeline_stopped = True

    # ── PHASE 4: SUMMARY 

    # Save pipeline report
    report_text, failed_steps = save_pipeline_report(results, steps_to_run, skipped_steps)

    # Print summary to terminal
    print(f"\n{'='*60}")
    print("PIPELINE COMPLETE")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print('='*60)
    print(report_text)
    print(f"Report saved to: data/output/pipeline_report.txt")

    # Return appropriate exit code
    if failed_steps:
        return 1
    elif not results and not skipped_steps:
        print("No steps were run.")
        return 0
    else:
        return 0


if __name__ == '__main__':
    sys.exit(main())
