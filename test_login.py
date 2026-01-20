import asyncio
from sunsynk.client import SunsynkClient

async def test():
    async with SunsynkClient('robert.dondo@gmail.com', 'M%TcEJvo9^j8di') as client:
        inverters = await client.get_inverters()
        print(f'✅ Login successful! Found {len(inverters)} inverter(s)')
        for inv in inverters:
            print(f'   - Inverter SN: {inv.sn}')

asyncio.run(test())
