from .models import User, Reserve_Parking_Spot, Parking_Lot
from flask_jwt_extended import current_user
from app import cache
from time import perf_counter_ns
@cache.cached(timeout=180, key_prefix='mall_data')
def get_mall_data():
    Lots=[]
    start = perf_counter_ns()
    lots=Parking_Lot.query.all()
    for lot in lots:
        lot_data={}
        lot_data['id']=lot.id
        lot_data['Name']=lot.prime_loc_name
        lot_data['Price']=lot.price
        lot_data['Address']=lot.address
        lot_data['pin_code']=lot.pin_code
        lot_data['max_spots']=lot.max_spots
        spots=lot.parking_spots
        # print(spots)
        lot_data['available']=len([spot for spot in spots if spot.status=='A'])
        Lots.append(lot_data)
    end = perf_counter_ns()
    print(f"Time taken to fetch mall data: {(end-start)/1e6} ms")
    return Lots

@cache.cached(timeout=120, key_prefix='all_users')
def get_users():
    start = perf_counter_ns()
    users=User.query.all()
    print(users)
    output=[]
    for user in users:
        user_data={}
        user_data['id']=user.id
        user_data['username']=user.username
        user_data['fullname']=user.fullname
        user_data['pincode']=user.pincode
        output.append(user_data)
    end = perf_counter_ns()
    print(f"Time taken to fetch all users: {(end-start)/1e6} ms")
    return output