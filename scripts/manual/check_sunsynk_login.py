"""Manual check that real Sunsynk credentials work end to end.

Hits the live Sunsynk API, so it is not part of the pytest suite. Reads
credentials from ``zuva/.env``:

    ./venv/bin/python scripts/manual/check_sunsynk_login.py
"""
import asyncio
import os
from dotenv import load_dotenv
from sunsynk.client import SunsynkClient

load_dotenv('zuva/.env')


async def main():
    username = os.getenv('SUNSYNK_USERNAME')
    password = os.getenv('SUNSYNK_PASSWORD')
    verification_code = os.getenv('SUNSYNK_VERIFICATION_CODE') or os.getenv('SUNSYNK_CODE')
    
    print(f"Testing Sunsynk API client...")
    print(f"Username: {username}")
    
    async with SunsynkClient(username, password, debug=True, verification_code=verification_code) as client:
        print("✅ Login successful!")
        
        # Get plants
        plants = await client.get_plants()
        print(f"\n📍 Found {len(plants)} plant(s):")
        for plant in plants:
            print(f"  - {plant}")
        
        # Get inverters
        inverters = await client.get_inverters()
        print(f"\n🔌 Found {len(inverters)} inverter(s):")
        for inverter in inverters:
            print(f"  - {inverter}")
        
        # Get realtime data for first inverter
        if inverters:
            sn = inverters[0].sn
            print(f"\n📊 Realtime data for inverter {sn}:")
            
            # Power values are watts, as reported by the inverter.
            battery = await client.get_inverter_realtime_battery(sn)
            print(f"  Battery: {battery.get_power():.0f} W, {battery.get_voltage():.1f} V, {battery.soc}% SoC")

            grid = await client.get_inverter_realtime_grid(sn)
            print(f"  Grid: {grid.get_power():.0f} W, {grid.get_voltage():.1f} V")

            input_data = await client.get_inverter_realtime_input(sn)
            print(f"  Input: {input_data.get_power():.0f} W, {input_data.get_voltage():.1f} V")

            output = await client.get_inverter_realtime_output(sn)
            print(f"  Output: {output.get_power():.0f} W, {output.get_voltage():.1f} V")


if __name__ == '__main__':
    asyncio.run(main())
