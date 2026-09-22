"""Enumerate and execute the actual launcher matrix; startup is not gameplay proof."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'src/launcher')]
import bootstrap
bootstrap.ensure_repo_paths()
import core
import presets
import real_exe_smoke as smoke
from src.display_plan import resolve_display_plan

SCHEMA = 'clash_launcher_resolution_sweep_v1'
BACKENDS = {'classic': core, **{name: importlib.import_module(name) for name in ('framed', 'completehd', 'modalwidgets')}}
REQUIRED_GAMEPLAY = ('map', 'scroll', 'minimap', 'army', 'castle', 'barracks', 'battle', 'save_reload', 'focus_recovery')


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode('utf-8')


def inventory(manifest=None):
    manifest = presets.load_manifest() if manifest is None else manifest
    presets.validate_manifest(manifest)
    if manifest['schema'] != 2 or set(manifest['profiles']) != set(BACKENDS):
        raise ValueError('Every launcher profile must have an explicit sweep backend')
    cases = []
    for profile, config in manifest['profiles'].items():
        for option in presets.load_options(manifest, profile):
            display = resolve_display_plan(renderer=profile, resolution=option.key)
            if display.stage != config['stage']:
                raise ValueError('Launcher and display stages differ')
            cases.append(dict(id=f'{profile}/{option.key}', profile=profile, resolution=option.key,
                              width=option.width, height=option.height, stage=display.stage,
                              recipe_revision=display.recipe_revision, display_plan=display.to_dict(),
                              advertised_status=option.status))
    return dict(schema=SCHEMA, manifest_sha256=hashlib.sha256(canonical(manifest)).hexdigest(),
                count=len(cases), cases=cases, custom_bounds=manifest.get('custom_bounds'),
                custom_exhaustively_executed=False, game_runtime_executed=False)


def aggregate(plan, rows):
    expected = {case['id']: case for case in plan['cases']}
    if not expected or len(expected) != len(plan['cases']):
        raise ValueError('Duplicate planned cases')
    seen, failures = {}, []
    for row in rows:
        key = row.get('id')
        if key not in expected or key in seen:
            raise ValueError('Unknown or duplicate observed case')
        case = expected[key]
        if any(row.get(field) != case[field] for field in ('profile', 'resolution', 'stage', 'recipe_revision')):
            raise ValueError('Observed case belongs to a different recipe')
        seen[key] = row
        if row.get('startup_passed') is not True:
            failures.append(key)
    missing = sorted(set(expected) - set(seen))
    gameplay_missing = {key: [name for name in REQUIRED_GAMEPLAY if row.get('gameplay', {}).get(name) is not True]
                        for key, row in seen.items()}
    return dict(schema=SCHEMA, manifest_sha256=plan['manifest_sha256'], expected=len(expected),
                observed=len(seen), missing=missing, startup_failures=failures,
                startup_matrix_passed=not missing and not failures,
                gameplay_missing=gameplay_missing,
                all_resolutions_working=not missing and not failures and not any(gameplay_missing.values()),
                custom_exhaustively_executed=False, promotion_ready=False, rows=rows)


def base_record(case):
    return {**{key: case[key] for key in ('id', 'profile', 'resolution', 'stage', 'recipe_revision')},
            'startup_passed': False, 'build_passed': False, 'gameplay': {}, 'errors': [],
            'manual_input_proof': False, 'promotion_ready': False}


def prepare(case, work, candidate_root):
    backend = BACKENDS[case['profile']]
    plan = backend.plan_candidate(resolution=case['resolution'], clash_dir=work, candidates_root=candidate_root)
    if (plan.renderer, plan.stage) != (case['profile'], case['stage']):
        raise ValueError('Prepared plan has a different profile/stage')
    result = backend.ensure_candidate(plan)
    if (result['output_sha256'] != smoke.sha(plan.candidate_exe)
            or result['display_plan']['recipe_revision'] != case['recipe_revision']):
        raise ValueError('Launcher candidate identity differs')
    backend.deploy_runtime_files(plan, result)
    if hasattr(backend, 'verify_launch'):
        backend.verify_launch(plan)
    return plan, result


def startup_audit(folder, case, log, returncode):
    snapshots = smoke.render(folder)
    result = smoke.outcome(log, returncode)
    end = next((line for line in log.splitlines() if line.startswith('REAL_END ')), '')
    result['survived_interval'] = ' entered=1 exited=0 exception_stop=0 ' in end
    result['primary_samples'] = len(snapshots)
    result['dimensions_match'] = len(snapshots) >= 2 and all(
        (row['width'], row['height']) == (case['width'], case['height']) for row in snapshots)
    result['nonblank_samples'] = bool(snapshots) and all(row['nonzero_indices'] > 20000 for row in snapshots)
    result['stable_primary_pair'] = len(snapshots) >= 2 and snapshots[-1]['raw_sha256'] == snapshots[-2]['raw_sha256']
    result['palette_observed'] = bool(snapshots) and all(row['palette_mode'] == 'paused_diagnostic_proxy_private_palette' for row in snapshots)
    result['passed'] = all(result[key] is True for key in ('observation_complete', 'survived_interval',
        'dimensions_match', 'nonblank_samples', 'stable_primary_pair', 'palette_observed'))
    result['samples'] = snapshots
    result['menu_visual_acceptance'] = False
    result['full_visible_composition'] = False
    result['gameplay_verified'] = False
    return result


def verify_proxy(path):
    manifest_path = path.with_name('ddraw_surfdump_proxy.build.json')
    metadata = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    if (metadata['generated_by'] != 'clash-hd-surface-dump-proxy'
            or metadata['output_sha256'].lower() != smoke.sha(path)
            or metadata['source_sha256'].lower() != smoke.sha(ROOT / 'src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp')):
        raise ValueError('Diagnostic proxy source or binary differs')
    return metadata


def execute(cases, reference, asset_manifest, out, proxy, seconds):
    if os.name != 'nt' or not 25 <= seconds <= 90:
        raise ValueError('Explicit native Windows bounded execution required')
    if out.exists() or not out.is_relative_to(Path('C:/ClashTests').resolve()) or any(
        out.is_relative_to(path) or path.is_relative_to(out) for path in (ROOT.resolve(), reference.resolve())):
        raise ValueError('Output must be new and isolated under C:/ClashTests')
    out.mkdir(parents=True)
    evidence = out / 'evidence'; evidence.mkdir()
    receipt = dict(schema=SCHEMA, source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                   source_sha256=smoke.sha(Path(__file__)), harness_sha256=smoke.sha(Path(smoke.__file__)),
                   asset_commit=smoke.ASSET_COMMIT, manifest_sha256=smoke.sha(asset_manifest),
                   rows=[], errors=[], game_runtime_executed=False, promotion_ready=False)
    manifest = json.loads(asset_manifest.read_text(encoding='utf-8-sig'))
    before = None
    try:
        before = smoke.verify(reference, manifest)
        receipt['proxy'] = verify_proxy(proxy)
        engine = smoke.compile_harness(out)
        receipt['engine_sha256'] = smoke.sha(engine)
        work = out / 'work'; shutil.copytree(reference, work)
        for name in manifest['runtime']['empty_directories']:
            target = work / name
            if not target.resolve().is_relative_to(work.resolve()):
                raise ValueError('Escaping runtime directory')
            target.mkdir(parents=True, exist_ok=True)
        candidate_root = out / 'candidates'
        for case in cases:
            row = base_record(case); receipt['rows'].append(row)
            launch_started = False
            cleanup_confirmed = False
            folder = evidence / case['profile'] / case['resolution']; folder.mkdir(parents=True)
            try:
                print('CASE BUILD ' + case['id'], flush=True)
                started = time.monotonic()
                plan, built = prepare(case, work, candidate_root)
                row.update(build_passed=True, build_seconds=round(time.monotonic()-started, 3),
                           candidate_sha256=built['output_sha256'], build_id=built['build_id'],
                           display_plan=built['display_plan'], source_identities=built.get('source_sha256', built.get('build_inputs')))
                (folder / 'launcher-plan.json').write_bytes(canonical(plan.to_dict()))
                (folder / 'launcher-build.json').write_bytes(canonical(built))
                shutil.copy2(plan.manifest_path, folder / 'launcher-deployment.json')
                executable = work / f"sweep_{case['profile']}_{case['resolution']}.exe"
                if executable.exists():
                    raise FileExistsError(executable)
                shutil.copy2(plan.candidate_exe, executable)
                original_wrapper = work / 'ddraw.dll'
                shipped_wrapper = reference / 'ddraw.dll'
                shutil.copy2(proxy, original_wrapper)
                try:
                    print('CASE EXECUTE ' + case['id'], flush=True)
                    start = time.monotonic()
                    launch_started = True
                    runtime = subprocess.run([str(engine), str(executable), str(folder), str(seconds), 'proxy'], cwd=work,
                        env={**os.environ, '_NT_SYMBOL_PATH': '.', '_NT_ALT_SYMBOL_PATH': '', 'CLASH_PROXY_PRESENT': '1'},
                        capture_output=True, text=True, errors='replace', timeout=seconds+100)
                    log = runtime.stdout + '\n' + runtime.stderr
                    (folder / 'debugger.log').write_text(log, encoding='utf-8', newline='\n')
                    receipt['game_runtime_executed'] = True
                    cleanup_confirmed = smoke.outcome(log, runtime.returncode)['owned_process_absent']
                    row['runtime_seconds'] = round(time.monotonic()-start, 3)
                    row['startup'] = startup_audit(folder, case, log, runtime.returncode)
                    row['candidate_unchanged'] = smoke.sha(executable) == built['output_sha256'] == smoke.sha(plan.candidate_exe)
                    row['original_unchanged'] = smoke.sha(work/'clash95.exe') == smoke.ORIGINAL_SHA256
                    row['startup_passed'] = row['startup']['passed'] and row['candidate_unchanged'] and row['original_unchanged']
                    row['debugger_log_sha256'] = smoke.sha(folder / 'debugger.log')
                finally:
                    shutil.copy2(shipped_wrapper, original_wrapper)
                    executable.unlink(missing_ok=True)
                if not row['startup']['owned_process_absent']:
                    raise RuntimeError('Owned process cleanup unconfirmed; do not launch another case')
            except Exception:
                row['errors'].append(traceback.format_exc())
                row['startup_passed'] = False
            (folder / 'result.json').write_bytes(canonical(row))
            (evidence / 'progress.json').write_bytes(canonical(receipt))
            print('CASE RESULT ' + case['id'] + ' ' + str(row['startup_passed']), flush=True)
            if launch_started and not cleanup_confirmed:
                receipt['errors'].append('Stop sweep: cleanup was not confirmed for ' + case['id'])
                break
    except Exception:
        receipt['errors'].append(traceback.format_exc())
    finally:
        try:
            receipt['original_inputs_unchanged'] = before is not None and smoke.verify(reference, manifest) == before
        except Exception:
            receipt['original_inputs_unchanged'] = False
            receipt['errors'].append(traceback.format_exc())
        (evidence / 'summary.json').write_bytes(canonical(receipt))
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=tuple(BACKENDS))
    parser.add_argument('--resolution', action='append')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--runtime', type=Path)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--proxy', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--seconds', type=int, default=30)
    args = parser.parse_args()
    plan = inventory()
    selected = [case for case in plan['cases'] if args.profile is None or case['profile'] == args.profile]
    if args.resolution:
        unknown = set(args.resolution) - {case['resolution'] for case in selected}
        if unknown:
            parser.error('Resolution is not advertised by the selected profile: ' + str(sorted(unknown)))
        selected = [case for case in selected if case['resolution'] in args.resolution]
    if not args.execute:
        print(json.dumps({**plan, 'cases': selected, 'selected': len(selected)}, indent=2))
        return 0
    if not all((args.runtime, args.manifest, args.proxy, args.out)):
        parser.error('Execution requires runtime, manifest, proxy and new output')
    result = execute(selected, args.runtime.resolve(), args.manifest.resolve(), args.out.resolve(), args.proxy.resolve(), args.seconds)
    final = aggregate({**plan, 'cases': selected}, result['rows'])
    (args.out / 'evidence/matrix.json').write_bytes(canonical(final))
    return int(not final['startup_matrix_passed'] or bool(result['errors']) or not result['original_inputs_unchanged'])


if __name__ == '__main__':
    raise SystemExit(main())
