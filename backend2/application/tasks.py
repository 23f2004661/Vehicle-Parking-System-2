from celery import shared_task
from .models import User, Reserve_Parking_Spot
from flask_jwt_extended import current_user
import csv
from datetime import datetime
from jinja2 import Template
from .mail import send_email
import requests

# task 1 Download CSV report for user 
# User(client) -> trigerred async job
@shared_task(ignore_result=False, name="download_csv_report")
def csv_report(user_name):
    user = User.query.filter_by(username=user_name).first()
    reservations = Reserve_Parking_Spot.query.filter(
    Reserve_Parking_Spot.user_id == user.id).all()
    print(f"length of the reservations is{len(reservations)}")
    csv_file_name = f"parking_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(f'static/{csv_file_name}','w',newline='') as csvfile:
        sr_no=1
        parking_csv = csv.writer(csvfile, delimiter=',')
        parking_csv.writerow(['Sr No','Lot Name','Spot ID','Parking Time','Leaving Time','Parking Cost','Vehicle Number'])
        for reservation in reservations:
            parking_csv.writerow([
                sr_no,
                reservation.lot_name,
                reservation.spot_id,
                reservation.parking_time_stamp,
                reservation.leaving_time_stamp,
                reservation.parking_cost,
                reservation.vehicle_number
            ])
            sr_no += 1
    return csv_file_name


#task 2 monthly report sent via mail
#sceduled vis cron tab
@shared_task(ignore_result=False, name="monthly_report_email")
def monthly_report():
    users = User.query.all()
    for user in users[1:]:
        user_data={}
        user_data['username'] = user.username
        user_reservations = Reserve_Parking_Spot.query.filter(
            Reserve_Parking_Spot.user_id == user.id,
            Reserve_Parking_Spot.leaving_time_stamp != None).all()
        print(user_reservations)
        lot_names = list(set([reservation.lot_name for reservation in user_reservations]))
        
        # Skip users with no reservations
        if not lot_names:
            continue
        
        user_data['lots_used'] = lot_names
        user_data["lots_stats"] = {}
        for lot in lot_names:
            total_cost = sum([reservation.parking_cost for reservation in user_reservations if reservation.lot_name == lot])
            total_visits = len([reservation for reservation in user_reservations if reservation.lot_name == lot])
            user_data["lots_stats"][lot] = {
                'total_cost': total_cost,
                'total_visits': total_visits
            }
        most_used_lot = max(lot_names, key=lambda lot: user_data["lots_stats"][lot]['total_visits'])
        user_data['most_used_lot'] = most_used_lot
        total_amount_spent = sum([user_data["lots_stats"][lot]['total_cost'] for lot in lot_names])
        user_data['total_amount_spent'] = total_amount_spent
        mail_template = """
        <h2>Monthly Parking Report</h2>
        <p>Dear {{ user_data.username }},</p>
        <p>Here is your parking report for the month:</p>
        <ul>
            {% for lot in user_data.lots_used %}
            <li>
                <strong>Lot Name:</strong> {{ lot }}<br>
                <strong>Total Visits:</strong> {{ user_data.lots_stats[lot].total_visits }}<br>
                <strong>Total Cost:</strong> ${{ user_data.lots_stats[lot].total_cost }}<br>
            </li>
            {% endfor %}
        </ul>
        <p><strong>Most Used Lot:</strong> {{ user_data.most_used_lot }}</p>
        <p><strong>Total Amount Spent:</strong> ${{ user_data.total_amount_spent }}</p>
        <p>Thank you for using our parking services!</p>
        """
        message = Template(mail_template).render(user_data=user_data)
        send_email(f"{user.username}@gmail.com",subject="Monthly Parking Report",message=message,content='html')
        

#task 3 Daily reminders to book a slot when a new parking lot is created sent via G-chat webhook
# Backend endpoint(triggered) async job
@shared_task(ignore_result=False, name="generate_msg")
def generate_msg(lot_name, address, pin_code, price, max_spots, username):
    message = f"Regards from the {username},\nA new parking lot '{lot_name}' has been added at {address}, Pin Code: {pin_code}. Price per hour: ${price}. Total Spots: {max_spots}. Book your spot now!"
    webhook_url = "https://chat.googleapis.com/v1/spaces/AAQAZetXD-c/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=1LphNcjXG638Vgg4fhHLHEPHnjS655Q7bsd9Bz-6XnI"
    payload = {
        "text": message
    }
    response = requests.post(webhook_url, json=payload)
    print(response.status_code)
    return "The deleivery is sent to the user"
