import asyncio
import os
from datetime import datetime, timezone

import aiohttp
from bson import CodecOptions
from pymongo import MongoClient
from pymongo.collection import Collection
from renault_api.renault_client import RenaultClient

mongo = MongoClient(os.environ['MONGODB_URI'])
db = mongo['myrenault']

mileage: Collection = db['mileage']
battery: Collection = db['battery'].with_options(codec_options=CodecOptions(tz_aware=True, tzinfo=timezone.utc))


async def check():
    print('Checking...')
    async with aiohttp.ClientSession() as websession:
        client = RenaultClient(websession=websession, locale='it_IT')
        await client.session.login(os.environ['EMAIL'], os.environ['PASSWORD'])

        account = await client.get_api_account(os.environ['ACCOUNT_ID'])
        vehicle = await account.get_api_vehicle(os.environ['VIN'])

        cockpit = await vehicle.get_cockpit()

        last_mileage = mileage.find_one(sort=[('timestamp', -1)])
        if last_mileage is None or last_mileage['mileage'] != cockpit.totalMileage:
            print(f'New mileage: {cockpit.totalMileage} km')
            mileage.insert_one({
                'timestamp': datetime.utcnow(),
                'mileage': cockpit.totalMileage,
            })

        battery_status = await vehicle.get_battery_status()
        new_timestamp = datetime.strptime(battery_status.timestamp, '%Y-%m-%dT%H:%M:%S%z')

        last_battery = battery.find_one(sort=[('timestamp', -1)])

        if last_battery is None or last_battery['timestamp'] != new_timestamp:
            print(f'New battery status: {battery_status}')
            battery.insert_one({
                'timestamp': new_timestamp,
                'batteryLevel': battery_status.batteryLevel,
                'batteryTemperature': battery_status.batteryTemperature,
                'batteryAutonomy': battery_status.batteryAutonomy,
                'batteryAvailableEnergy': battery_status.batteryAvailableEnergy,
                'plugStatus': battery_status.plugStatus,
                'chargingStatus': battery_status.chargingStatus,
                'chargingRemainingTime': battery_status.chargingRemainingTime,
                'chargingInstantaneousPower': battery_status.chargingInstantaneousPower,
            })
    print('Done!')


if __name__ == '__main__':
    asyncio.run(check())
