from app import db

class Donations(db.Model):
    __tablename__ = "donations"
    ecref = db.Column(db.String, primary_key=True)
    added_date = db.Column(db.Date)
    entity_name = db.Column(db.String)
    value = db.Column(db.Numeric)
    accepted_date = db.Column(db.String)
    donor_name = db.Column(db.String)
    donor_status = db.Column(db.String)
    donee_type = db.Column(db.String)
    donation_type = db.Column(db.String)
    nature_of_donation = db.Column(db.String)
    received_date = db.Column(db.Date)
    attempt_conceal = db.Column(db.String)