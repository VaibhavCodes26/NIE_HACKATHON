import httpx

destinations = ['mysuru', 'bengaluru', 'hampi', 'gokarna']
print('=== TESTING BACKEND WEATHER ENDPOINT FOR KARNATAKA DESTINATIONS ===')
for d in destinations:
    resp = httpx.get(f'http://127.0.0.1:8000/api/weather/forecast?destination={d}', timeout=10)
    print(f'Destination {d:12s} -> Status: {resp.status_code}')
    if resp.status_code == 200:
        data = resp.json()
        daily = data.get('daily', [])
        f0 = daily[0] if daily else {}
        source = data.get('source')
        print(f"   Source: {source} | Days: {len(daily)}")
        print(f"   Date: {f0.get('date')} | Temp: {f0.get('temperature_min_c')}C - {f0.get('temperature_max_c')}C | Rain: {f0.get('precipitation_probability_max')}% | Code: {f0.get('weather_code')}")
    else:
        print(f"   Error: {resp.text}")
