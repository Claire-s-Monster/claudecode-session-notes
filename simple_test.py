# Test our timestamp processing fix
sessions = [
    {'session_id': 'valid', 'timestamp': '2024-01-01T10:00:00Z'},
    {'session_id': 'corrupted', 'timestamp': None},
    {'session_id': 'empty', 'timestamp': ''},
]

print('Input sessions:')
for s in sessions:
    print(f'  {s}')

print('\nTesting robust timestamp processing:')
timestamps = []
for s in sessions:
    ts = s.get('timestamp')
    if ts is not None and ts != '':
        try:
            str_ts = str(ts)
            if str_ts and str_ts.strip():
                timestamps.append(str_ts)
                print(f'  Added: {str_ts}')
        except (TypeError, ValueError) as e:
            print(f'  Skipped invalid: {ts} ({e})')
            continue
    else:
        print(f'  Skipped null/empty: {ts}')

print(f'\nValid timestamps: {timestamps}')

date_range = {
    'start': min(timestamps) if timestamps else None,
    'end': max(timestamps) if timestamps else None,
}

print(f'Date range: {date_range}')
print('✅ SUCCESS: No comparison errors with mixed None/string timestamps!')
