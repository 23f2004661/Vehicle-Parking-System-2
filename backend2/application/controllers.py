from flask_jwt_extended import current_user, jwt_required,create_access_token, get_jwt_identity
from flask import current_app as app,request, jsonify, abort,send_from_directory
from .models import User,Parking_Lot,Parking_Spot,Reserve_Parking_Spot
from .database import db
from functools import wraps
from datetime import datetime
import json
import math
from sqlalchemy import and_
import matplotlib.pyplot as plt
import sys
import os
from .tasks import csv_report,monthly_report,generate_msg
from celery.result import AsyncResult

def role_required(role):
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def give_access(*args, **kwargs):
            if current_user.role != role:
                return jsonify('Unauthorized'), 403
            return fn(*args, **kwargs)
        return give_access
    return wrapper

@app.route('/login',methods=['POST'])
def login():
    username=request.json.get('username',None)
    password=request.json.get('password',None)
    
    user=User.query.filter_by(username=username).one_or_none()
    if not user or not user.password==password:
        return jsonify({"msg":"Bad username or password"}),401
        
    role=user.role
    access_token=create_access_token(identity=user)
    return jsonify(access_token=access_token,role=role)

@app.route('/register',methods=['POST'])
def register():
    username=request.json.get("username",None)
    pincode=request.json.get("pincode",None)
    password=request.json.get("password",None)
    fullname=request.json.get("fullname",None)
    user=User.query.filter_by(username=username).first()

    if user:
        return jsonify("user already exists"),400

    user = User(username=username,password=password,pincode=pincode,fullname=fullname)
    db.session.add(user)
    db.session.commit()
    return jsonify("user added"),200

@app.route('/api/createLot',methods=['POST'])
@role_required("admin")
def createLot():
    Prime_loc_name = request.json.get('prime_loc_name')
    Price = request.json.get('price')
    address = request.json.get('address')
    pin_code = request.json.get('pin_code')
    max_spots = request.json.get('max_spots')
    max_spots=int(max_spots)

    exisisting_lot=Parking_Lot.query.filter_by(prime_loc_name=Prime_loc_name).first()
    if exisisting_lot:
        print("Lot exists")
        return {"message":"Lot already exists"},409
    else:
        parking_lot=Parking_Lot(prime_loc_name=Prime_loc_name,price=Price,address=address,pin_code=pin_code,max_spots=max_spots)
        db.session.add(parking_lot)
        db.session.commit()
        for i in range(max_spots):
            spot = Parking_Spot(
            lot_id=parking_lot.id,
            status='A'
            )
            db.session.add(spot)
        db.session.commit()
        username = current_user.username
        print("Lot created")
        res = generate_msg.delay(Prime_loc_name, address, pin_code, Price, max_spots,username)
        print(f"Generated message task with id: {res.id}")
        print(f"the result is {res.result}")
        return {"message":"Lot created Successfully"},200

@app.route('/api/Users',methods=['GET'])
@role_required("admin")
def get_all_users():
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
    return jsonify({"users":output}),200


@app.route('/api/ParkingLots',methods=['GET'])
@role_required("admin")
def ParkingLots():
    Lots=[]
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
    return jsonify({"Lots":Lots}),200

@app.route('/api/edit_lot/<int:lot_id>', methods=['POST'])
@role_required("admin")
def edit_lot(lot_id):
    if request.method == 'POST':
        lot = Parking_Lot.query.get(lot_id)
        Price = request.json.get('price')
        address = request.json.get('address')
        pin_code = request.json.get('pin_code')
        max_spots = request.json.get('max_spots')
        print(Price,address,pin_code,max_spots)
        max_spots=int(max_spots)

        occupied_spots = [spot for spot in lot.parking_spots if spot.status == 'O']
        
        if max_spots < len(occupied_spots):
            print("Cannot reduce max spots below number of occupied spots.")
            return {"message": "Cannot reduce max spots below number of occupied spots."}, 400
        

        lot.price = Price
        lot.Address = address
        lot.pin_code = pin_code
        
        if max_spots > lot.max_spots:

            for _ in range(max_spots - lot.max_spots):
                spot = Parking_Spot(lot_id=lot.id, status='A')
                db.session.add(spot)

            lot.max_spots = max_spots
            db.session.commit()
            print("Lot updated: spots added.")
            return {"message": "Lot updated: spots added."}, 200
        elif max_spots < lot.max_spots:
            removable_spots = [spot for spot in lot.parking_spots if spot.status != 'O']
            spots_to_remove = lot.max_spots - max_spots
            if len(removable_spots) < spots_to_remove:
                return {"message": "Not enough available spots to remove."}, 400
            for spot in removable_spots[:spots_to_remove]:
                db.session.delete(spot)
            lot.max_spots = max_spots
            db.session.commit()
            print("Lot updated: spots removed.")
            return {"message": "Lot updated: spots removed."}, 200
        else:
            db.session.commit()
            return {"message": "Lot updated."}, 200

@app.route('/api/delete_lot/<int:lot_id>',methods=['DELETE'])
@role_required("admin")
def delete_lot(lot_id):
    lot=Parking_Lot.query.get(lot_id)
    if not lot:
        return {"message":"Lot not found."},404
    else:
        db.session.delete(lot)
        occupied_spots=[spot for spot in lot.parking_spots if spot.status == 'O']
        if len(occupied_spots) > 0:
            return {"message":"Cannot delete lot with occupied spots."},400
        else:
            db.session.delete(lot)
            db.session.commit()
            return {"message":"Lot deleted successfully."},200

@app.route('/api/mallData',methods=['GET'])
@jwt_required()
def getMallData():
    Lots=[]
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
    return jsonify({"Lots":Lots}),200

@app.route('/api/book/<int:lot_id>', methods=['POST'])
@jwt_required()
def book(lot_id):
    lot = Parking_Lot.query.get(lot_id)
    v_n=request.json.get('v_n')
    print(v_n)
    booked_spots = [spot for spot in lot.parking_spots if spot.status == 'O']
    if len(booked_spots) == int(lot.max_spots):
        return {"message":"No available spots!"},400
    else:
        username = current_user.username
        user = User.query.filter_by(username=username).first()

        last_reservation = (
            Reserve_Parking_Spot.query
            .filter_by(user_id=user.id)
            .order_by(Reserve_Parking_Spot.id.desc())
            .first()
        )

        if last_reservation and last_reservation.leaving_time_stamp is None:
            return {"message": "User already has an active reservation."}, 400
        else:
            first_available_spot = (
                Parking_Spot.query
                .filter_by(lot_id=lot_id, status='A')
                .order_by(Parking_Spot.id)
                .first()
            )

            first_available_spot.status = 'O'
            new_reservation = Reserve_Parking_Spot(
                lot_name=lot.prime_loc_name,
                user_id=user.id,
                spot_id=first_available_spot.id,
                parking_time_stamp=datetime.utcnow(),
                leaving_time_stamp=None,
                parking_cost=None,
                vehicle_number=v_n
            )
            db.session.add(new_reservation)
            db.session.commit()
            return {"message":"Spot booked successfully!"},200


@app.route('/user/history')
@jwt_required()
def user_history():
    username=current_user.username
    print(username)
    user=User.query.filter_by(username=username).first()
    print(user.id)
    Reservations=Reserve_Parking_Spot.query.filter_by(user_id=user.id).all()
    print(Reservations)
    history=[]
    for reservation in Reservations:
        obj={}
        obj['lot_name']=reservation.lot_name
        obj['spot_id']=reservation.spot_id
        obj['parking_time_stamp']=reservation.parking_time_stamp
        obj['leaving_time_stamp']=reservation.leaving_time_stamp
        obj['parking_cost']=reservation.parking_cost
        history.append(obj)
    return {"history": history},200

@app.route('/api/user/release',methods=['GET','POST'])
@jwt_required()
def release():
    if request.method == 'GET':
        username=current_user.username
        user=User.query.filter_by(username=username).first()
        reservation=Reserve_Parking_Spot.query.filter(and_(Reserve_Parking_Spot.user_id==user.id, Reserve_Parking_Spot.leaving_time_stamp.is_(None))).first()
        reservation.leaving_time_stamp=datetime.utcnow()
        lot=Parking_Lot.query.filter_by(prime_loc_name=reservation.lot_name).first()
        duration = reservation.leaving_time_stamp - reservation.parking_time_stamp
        hours = duration.total_seconds() / 3600
        slabs = math.ceil(hours) 
        lot.price = int(lot.price)  
        reservation.parking_cost = slabs * lot.price
        details={
            "lot_name": reservation.lot_name,
            "parking_time": reservation.parking_time_stamp,
            "leaving_time": reservation.leaving_time_stamp,
            "vehicle_number": reservation.vehicle_number,
            "parking_cost": reservation.parking_cost
        }
        return details,200

    else:
        username=current_user.username
        user=User.query.filter_by(username=username).first()
        reservation=Reserve_Parking_Spot.query.filter(and_(Reserve_Parking_Spot.user_id==user.id, Reserve_Parking_Spot.leaving_time_stamp.is_(None))).first()
        reservation.leaving_time_stamp=datetime.utcnow()
        lot=Parking_Lot.query.filter_by(prime_loc_name=reservation.lot_name).first()
        duration = reservation.leaving_time_stamp - reservation.parking_time_stamp
        hours = duration.total_seconds() / 3600
        slabs = math.ceil(hours)  
        lot.price = int(lot.price) 
        reservation.parking_cost = slabs * lot.price
        spot=Parking_Spot.query.filter_by(id=reservation.spot_id).first()
        print(spot.id)
        print(spot.status)
        spot.status='A'
        db.session.commit()
        message=json.dumps({"message": "Spot Release successfully"})
        return message,200

@app.route("/api/user/summary")
@jwt_required()
def get_user_summary():
    username=current_user.username
    user=User.query.filter_by(username=username).first()
    user_reservations = Reserve_Parking_Spot.query.filter_by(user_id=user.id).all()

    lots=Parking_Lot.query.all()
    lots_name=[lot.prime_loc_name for lot in lots]
    lots_by_use={}
    for lot in lots_name:
        lots_by_use[lot] = 0
    for resrvation in user_reservations:
        if resrvation.lot_name in lots_name:
            lots_by_use[resrvation.lot_name] += 1
    plt.clf()
    plt.figure(figsize=(6,6))
    plt.bar(x=lots_name,height=lots_by_use.values())
    plt.xticks(rotation=45)
    plt.ylabel('Usage')
    plt.title("Most used Lots")
    print(os.getcwd())
    plt.savefig('../frontend/src/assets/user_bar.png')
    plt.close()
    return {"message": "Its working right Now"},200

@app.route("/api/admin/summary")
@role_required("admin")
def get_admin_summary():
    reservations = Reserve_Parking_Spot.query.filter(Reserve_Parking_Spot.parking_cost != None).all()
    lots = Parking_Lot.query.all()
    lots_prices = {}
    for lot in lots:
        lots_prices[lot.prime_loc_name] = 0

    valid_lot_names = {lot.prime_loc_name for lot in lots}
    lots_labels = [lot.prime_loc_name for lot in lots]

    # 1. Aggregate the prices into lots_prices
    for reservation in reservations:
        if reservation.lot_name in valid_lot_names:
            lots_prices[reservation.lot_name] += int(reservation.parking_cost)

    # 2. Remove zero-value lots
    lots_prices_0 = []
    lots_labels_0 = []

    keys_to_remove = [lot for lot, price in lots_prices.items() if price == 0]

    for lot in keys_to_remove:
        lots_prices_0.append(lots_prices.pop(lot))
        lots_labels_0.append(lot)
        lots_labels.remove(lot) 

    lots_values = list(lots_prices.values())

    plt.clf()
    plt.figure(figsize=(5,5))
    plt.pie(lots_values, labels=lots_labels, autopct='%1.1f%%', startangle=90)
    plt.tight_layout()
    plt.title("Revenue Generated by Lots")
    plt.savefig('../frontend/src/assets/pie.png', bbox_inches="tight")
    plt.close()

    lots_occupied={}
    for lot in lots:
        lots_occupied[lot.prime_loc_name] = [lot.max_spots,0]
    spots_occupied=Parking_Spot.query.filter(Parking_Spot.status=='O').all()
    for spot in spots_occupied:
        lot_id=spot.lot_id
        lot=Parking_Lot.query.get(lot_id)
        lots_occupied[lot.prime_loc_name][1]+=1
    lots_name = list(lots_occupied.keys())
    lots_max_cap = [v[0] for v in lots_occupied.values()]  
    lots_occ = [v[1] for v in lots_occupied.values()]      
    lots_avail = [max_cap - occ for max_cap, occ in zip(lots_max_cap, lots_occ)]  
    plt.clf()
    plt.bar(lots_name, lots_occ, label='Occupied', color='green')
    plt.bar(lots_name, lots_avail, bottom=lots_occ, label='Available', color='lightgray')
    plt.title("Occupied and Available Spots in Every Lot")
    plt.ylabel("Number of Spots")
    plt.xlabel("Parking Lot")
    plt.xticks(rotation=45)
    plt.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig('../frontend/src/assets/bar.png',bbox_inches="tight")
    plt.close()
    return {"message":"Image Saved"},200

@app.route('/api/check_status/<int:lot_id>')
@role_required("admin")
def check_status(lot_id):
    lot=Parking_Lot.query.get(lot_id)
    reservations=Reserve_Parking_Spot.query.filter_by(lot_name=lot.prime_loc_name).all()
    reservations_occupied=[reservation for reservation in reservations if reservation.leaving_time_stamp == None]
    user_ids=[]
    for reservation in reservations_occupied:
        user_ids.append(reservation.user_id)
    print(reservation)
    usernames=[]
    for id in user_ids:
        user = User.query.filter_by(id=id).first()
        usernames.append(user.username)
    details=[]
    for (i,reservation) in enumerate(reservations_occupied):
        detail={
            "id": reservation.id,
            "username": usernames[i],
            "lot_name": reservation.lot_name,
            "spot_number": reservation.spot_id,
            "vehicle_number": reservation.vehicle_number,
            "parking_time_stamp": reservation.parking_time_stamp 
        }
        details.append(detail)
    print(details)
    return {"details": details},200

# backend jobs trigger
from flask import jsonify

@app.route('/export_csv')
@jwt_required()
def export():
    username = current_user.username
    result = csv_report.delay(username)
    return jsonify({"task_id": str(result.id), "status": "processing","result":result.result}), 202

@app.route('/api/csv_result/<id>')
def csv_result(id):
    res = AsyncResult(id)

    if not res.ready():
        return jsonify({"status": "pending"}), 202

    filename = res.result  # your task returns filename
    return send_from_directory("static", filename, as_attachment=True)

@app.route('/api/send_mail')
def send_mail():
    res = monthly_report.delay()
    return jsonify({"task_id": str(res.id), "status": "processing","result":res.result}), 202