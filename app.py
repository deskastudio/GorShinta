import calendar
from curses import flash
from datetime import timedelta
import datetime
from io import BytesIO
import os
import re
import uuid
import bcrypt
from bson import ObjectId
from flask import Flask, jsonify, make_response, render_template, request, redirect, send_file, url_for, session, flash
from flask_wtf import FlaskForm
import pymongo
from wtforms import StringField, EmailField, PasswordField
from wtforms.validators import InputRequired, Length, Email
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from pymongo import MongoClient
from flask_pymongo import PyMongo
from datetime import datetime, timedelta, timezone
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors

# from distutils.command import build
app = Flask(__name__)
app.secret_key = 'sjdcasjbcsabfh'

password = 'sparta'
cxn_str = f"mongodb://test:{password}@ac-zunxf5x-shard-00-00.k72y7zu.mongodb.net:27017,ac-zunxf5x-shard-00-01.k72y7zu.mongodb.net:27017,ac-zunxf5x-shard-00-02.k72y7zu.mongodb.net:27017/?ssl=true&replicaSet=atlas-j2cl22-shard-0&authSource=admin&retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(cxn_str)

db = client.gor_sinta
users_collection = db.users
bookings_collection = db.bookings
payments_collection = db.payments
dataLapangan_collection = db.dataLapangan
dataGaleri_collection = db.dataGaleri
dataKontak_collection = db.dataKontak
dataTentang_collection = db.dataTentang
dataReview_collection = db.dataReview
dataPembayaran_collection = db.dataPembayaran
dataAdmin_collection = db.dataAdmin

UPLOAD_FOLDER = '/static'  # Ganti dengan path folder upload Anda
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'heic'}  # Ekstensi file yang diizinkan

# Inisialisasi Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    pass

@login_manager.user_loader
def load_user(user_id):
    user_data = users_collection.find_one({'_id': ObjectId(user_id)})
    if user_data:
        user = User()
        user.id = str(user_data['_id'])
        return user
    return None

def set_login_time():
    session['login_time'] = datetime.utcnow()
    
# Fungsi untuk memeriksa waktu login
def check_login_time():# Periksa apakah waktu login sudah ditetapkan
    if 'login_time' in session:
        login_time = session['login_time']
        current_time = datetime.now(timezone.utc)  # Ubah ke objek waktu yang sadar zona waktu
        time_difference = current_time - login_time
        if time_difference.total_seconds() > LOGOUT_TIME_SECONDS:
            session.clear()
            flash('Anda telah logout otomatis karena tidak aktif.')
            return redirect(url_for('login'))

LOGOUT_TIME_SECONDS = 1800  # Contoh: logout otomatis setelah 30 menit tidak aktif

@app.route('/')
def index():
    dataLapangan = dataLapangan_collection.find({})
    dataGaleri = dataGaleri_collection.find({})
    dataKontak = dataKontak_collection.find_one()
    dataTentang = dataTentang_collection.find_one()
    dataReview = dataReview_collection.find({})
    alert_message = session.pop('alert_message', 'Selamat Datang di Gor Shinta semoga Anda senang')
    return render_template('index.html', alert_message=alert_message, dataLapangan=dataLapangan, dataGaleri=dataGaleri, dataKontak=dataKontak, dataTentang=dataTentang, dataReview=dataReview)

@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    else:
        fullname = request.form['fullname']
        phone_number = request.form['phone_number']
        email = request.form['email']
        password1 = request.form['password1'].encode('utf-8')
        password2 = request.form['password2'].encode('utf-8')
        hash_password = bcrypt.hashpw(password1, bcrypt.gensalt())
        
        if not fullname or not phone_number or not email or not password1 or not password2:
            flash('Please fill in all fields')
            return redirect(url_for('register'))
        
        if len(password1) < 8:
            flash('Password must be at least 8 characters long')
            return redirect(url_for('register'))
        
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            flash('Invalid email address')
            return redirect(url_for('register'))
        
        if not re.match(r'^\+?1?\d{9,15}$', phone_number):
            flash('Invalid phone number')
            return redirect(url_for('register'))

        if password1 != password2:
            flash('Passwords do not match')
            return redirect(url_for('register'))

        if users_collection.find_one({'email': email}): 
            flash('Email already exists')
            return redirect(url_for('register'))
        
        new_user = {
            'fullname': fullname,
            'phone_number': phone_number,
            'email': email,
            'password': hash_password
        }

        user_id = users_collection.insert_one(new_user).inserted_id
        set_login_time()
        session['user_id'] = str(user_id)
        session['email'] = email
        session['fullname'] = fullname
        session['phone_number'] = phone_number
        return redirect(url_for('login'))

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = users_collection.find_one({'email': email})

        if user is not None and len(user) > 0:
            if bcrypt.checkpw(password.encode('utf-8'), user['password']):
                user_obj = User()
                user_obj.id = str(user['_id'])
                login_user(user_obj)
                session['fullname'] = user['fullname']
                session['email'] = user['email']
                session['user_id'] = str(user['_id'])
                session['phone_number'] = user['phone_number']
                
                set_login_time()
                
                return redirect(url_for('selectField'))

            else:
                flash("Invalid email or password")
                return redirect(url_for('login'))
        else:
            flash("Gagal, User tidak ditemukan")
            return redirect(url_for('login'))
    else:
        return render_template('login.html')
    
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/selectField')
@login_required
def selectField():
    dataLapangan = list(db.dataLapangan.find({}))
    fullname = session.get('fullname') 
    check_login_time()   
    return render_template('selectField.html', fullname=fullname, dataLapangan=dataLapangan)

@app.route('/selectTime/<string:_id>', methods=['GET', 'POST'])
@login_required
def selectTime(_id):
    dataLapangan = list(db.dataLapangan.find({"_id": ObjectId(_id)}))
    
    fullname = session.get('fullname')
    phone_number = session.get('phone_number')
    email = session.get('email')
    
    alert_message = 'Silahkan pilih waktu yang tersedia.'
    
    if request.method == 'POST':
        selected_date = request.form.get('selected_date')
        selected_time = request.form.get('selected_time')
        selected_sport = request.form.get('selected_sport')
        selected_court = request.form.get('selected_court')
        selected_price = request.form.get('selected_price')
        
        # Cek apakah waktu dan tanggal yang dipilih sudah dipesan
        existing_booking = db.payments.find_one({
            'selected_date': selected_date,
            'selected_time': selected_time,
            'selected_court': selected_court
        })
        
        if existing_booking:
            alert_message = 'Waktu dan tanggal yang dipilih sudah dipesan. Silakan pilih waktu yang lain.'
            return render_template('selectTime.html', fullname=fullname, phone_number=phone_number, email=email, dataLapangan=dataLapangan, alert_message=alert_message)
        
        # Simpan data pemesanan ke sesi
        session['booking_data'] = {
            'fullname': fullname,
            'phone_number': phone_number,
            'email': email,
            'selected_date': selected_date,
            'selected_time': selected_time,
            'selected_sport': selected_sport,
            'selected_court': selected_court,
            'selected_price': selected_price
        }
        
        # Simpan pesan alert ke sesi
        session['alert_message'] = 'Berhasil di pesanan. Silahkan pilih metode pembayaran.'
        
        # Alihkan ke halaman pembayaran
        return redirect(url_for('payment'))
    
    return render_template('selectTime.html', fullname=fullname, phone_number=phone_number, email=email, dataLapangan=dataLapangan, alert_message=alert_message)

@app.route('/payment', methods=['GET', 'POST'])
@login_required
def payment():
    dataPembayaran = list(db.dataPembayaran.find({}))
    fullname = session.get('fullname')
    booking_data = session.get('booking_data')
    alert_message = session.pop('alert_message', 'Silahkan pilih metode pembayaran.')
    
    if not booking_data:
        alert_message = 'Tidak ada data pemesanan yang ditemukan. Silakan lakukan pemesanan terlebih dahulu.'
        return redirect(url_for('selectTime', _id=booking_data['_id'])) 
    
    if request.method == 'POST':
        payment_type = request.form.get('payment_type')
        payment_method = request.form.get('payment_method')
        payment_proof = request.files.get('payment_proof')
        
        if not payment_type or not payment_method:
            session['alert_message'] = 'Pilih metode pembayaran terlebih dahulu.'
            return redirect(url_for('payment'))
        
        if payment_proof:
            nama_file_asli = payment_proof.filename
            nama_file_foto = secure_filename(nama_file_asli)
            file_path = f'./static/img/{nama_file_foto}'
            payment_proof.save(file_path)
        else:
            nama_file_foto = None

        # Simpan data pembayaran dan pemesanan ke MongoDB
        db.payments.insert_one({
            'fullname': booking_data['fullname'],
            'phone_number': booking_data['phone_number'],
            'email': booking_data['email'],
            'selected_date': booking_data['selected_date'],
            'selected_time': booking_data['selected_time'],
            'selected_sport': booking_data['selected_sport'],
            'selected_court': booking_data['selected_court'],
            'selected_price': booking_data['selected_price'],
            'payment_type': payment_type,
            'payment_method': payment_method,
            'payment_proof': nama_file_foto
        })
        
        session['alert_message'] = 'Pembayaran Berhasil! Terimakasih sudah ingin bermain di Gor Sinta.'
        return redirect(url_for('index'))
    
    return render_template('payment.html', fullname=fullname, booking_data=booking_data, alert_message=alert_message, dataPembayaran=dataPembayaran)

@app.route('/datadiri', methods=['GET', 'POST'])
@login_required
def datadiri():
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        email = request.form.get('email')
        phone_number = request.form.get('phone_number')
        alamat = request.form.get('alamat')
        foto = request.files.get('foto')

        # Temukan pengguna di database untuk mendapatkan informasi foto saat ini
        user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
        old_foto_path = user.get('foto')

        update_data = {
            'fullname': fullname,
            'email': email,
            'phone_number': phone_number,
            'alamat': alamat
        }

        if foto:
            nama_file_asli = foto.filename
            nama_file_foto = secure_filename(nama_file_asli)
            file_path = os.path.join('static/img/imgProfile', nama_file_foto)  # Updated path to be relative to static folder
            
            # Ensure the directory exists
            if not os.path.exists(os.path.dirname(file_path)):
                os.makedirs(os.path.dirname(file_path))

            foto.save(file_path)
            update_data['foto'] = file_path  # Store the relative path

            # Hapus foto lama jika ada dan hanya jika berhasil menyimpan foto baru
            if old_foto_path and os.path.exists(old_foto_path):
                os.remove(old_foto_path)

        users_collection.update_one(
            {'_id': ObjectId(session['user_id'])},
            {'$set': update_data}
        )

        flash('Profil berhasil diperbarui')
        return redirect(url_for('datadiri'))

    user_fullname = session.get('fullname')
    users = users_collection.find_one({'_id': ObjectId(session['user_id'])})

    return render_template('dataDiri.html', fullname=user_fullname, users=users)


@app.route('/adminDataLapangan', methods=['GET'])
def admin_data_lapangan():
    dataLapangan = list(db.dataLapangan.find({}))
    return render_template('adminDataLapangan.html', dataLapangan=dataLapangan)

@app.route('/tambahDataLapangan', methods=['GET', 'POST'])
def tambah_data_lapangan():
    if request.method == 'POST':
        jenis_lapangan = request.form['jenis_lapangan']
        harga_lapangan = request.form['harga_lapangan']
        nama_lapangan = request.form['nama_lapangan']
        foto_lapangan = request.files['foto_lapangan']
        deskripsi_lapangan = request.form['deskripsi_lapangan']
        
        if foto_lapangan:
            nama_file_asli = foto_lapangan.filename
            nama_file_foto = secure_filename(nama_file_asli)
            file_path = f'./static/img/{nama_file_foto}'
            foto_lapangan.save(file_path)
        else:
            nama_file_foto = None
            
        dataLapangan_collection.insert_one({
            'jenis': jenis_lapangan,
            'harga': harga_lapangan,
            'nama': nama_lapangan,
            'foto': nama_file_foto,
            'deskripsi': deskripsi_lapangan
        })
        
        return redirect(url_for("admin_data_lapangan"))
        
    return render_template('tambahDataLapangan.html')

@app.route('/editDataLapangan/<string:_id>', methods=["GET", "POST"])
def edit_data_lapangan(_id):
    if request.method == 'POST':
        jenis_lapangan = request.form['jenis_lapangan']
        harga_lapangan = request.form['harga_lapangan']
        nama_lapangan = request.form['nama_lapangan']
        foto_lapangan = request.files['foto_lapangan']
        
        if foto_lapangan:
            nama_file_asli = foto_lapangan.filename
            nama_file_foto = secure_filename(nama_file_asli)
            file_path = f'./static/img/{nama_file_foto}'
            foto_lapangan.save(file_path)
            
            db.dataLapangan.update_one({'_id': ObjectId(_id)}, {'$set': {
                'jenis': jenis_lapangan,
                'harga': harga_lapangan,
                'nama': nama_lapangan,
                'foto': nama_file_foto
            }})
        else:
            db.dataLapangan.update_one({'_id': ObjectId(_id)}, {'$set': {
                'jenis': jenis_lapangan,
                'harga': harga_lapangan,
                'nama': nama_lapangan
            }})
        
        return redirect(url_for('admin_data_lapangan'))
    
    data = db.dataLapangan.find_one({'_id': ObjectId(_id)})
    return render_template('tambahDataLapangan.html', data=data)

@app.route('/hapusDataLapangan/<string:_id>', methods=["GET", "POST"])
def delete_data_lapangan(_id):
    db.dataLapangan.delete_one({'_id': ObjectId(_id)})
    return redirect(url_for('admin_data_lapangan'))

@app.route('/kontak', methods=['GET', 'POST'])
def kontak():
    data_kontak = dataKontak_collection.find_one()  # Mengambil satu data saja, karena asumsi hanya ada satu entri untuk kontak
    if request.method == 'POST':
        email_admin = request.form['email_admin']
        noTelepon_admin = request.form['noTelepon_admin']
        alamat_admin = request.form['alamat_admin']
        maps_admin = request.form['maps_admin']
        
        # Memasukkan atau mengupdate data kontak ke dalam database
        dataKontak_collection.update_one({}, {'$set': {
            'email_admin': email_admin,
            'noTelepon_admin': noTelepon_admin,
            'alamat_admin': alamat_admin,
            'maps_admin': maps_admin
        }}, upsert=True)
        
    return render_template('adminKontak.html', data_kontak=data_kontak)

@app.route('/tentang', methods=['GET', 'POST'])
def tentang():
    data_tentang = dataTentang_collection.find_one()  
    
    if request.method == 'POST':
        judul_admin = request.form['judul_admin']
        deskripsi_admin = request.form['deskripsi_admin']
        
        # Memasukkan atau mengupdate data kontak ke dalam database
        dataTentang_collection.update_one({}, {'$set': {
            'judul_admin': judul_admin,
            'deskripsi_admin': deskripsi_admin
        }}, upsert=True)  # upsert=True memastikan data akan diupdate jika sudah ada, atau dimasukkan jika belum ada
    return render_template('adminTentang.html', data_tentang=data_tentang)

@app.route('/review', methods=['GET'])
def review():
    dataReview = list(db.dataReview.find({}))
    return render_template('adminReview.html', dataReview=dataReview)

@app.route('/hapusReview/<string:_id>', methods=["GET", "POST"])
def delete_data_review(_id):
    db.dataReview.delete_one({'_id': ObjectId(_id)})
    return redirect(url_for('review'))

@app.route('/adminDataAkun', methods=['GET'])
def admin_data_akun():
    admin = list(db.dataAdmin.find({}))
    return render_template('adminDataAkun.html', admin=admin)

@app.route('/tambahDataAdmin', methods=['GET', 'POST'])
def tambah_data_admin():
    if request.method == 'GET':
        return render_template('tambahDataAdmin.html')
    else:
        username = request.form['username']
        password1 = request.form['password1'].encode('utf-8')
        password2 = request.form['password2'].encode('utf-8')
        hash_password = bcrypt.hashpw(password1, bcrypt.gensalt())
        
        if not username or not password1 or not password2:
            flash('Please fill in all fields')
            return redirect(url_for('tambah_data_admin'))
        
        if len(password1) < 8:
            flash('Password must be at least 8 characters long')
            return redirect(url_for('tambah_data_admin'))

        if password1 != password2:
            flash('Passwords do not match')
            return redirect(url_for('tambah_data_admin'))

        if users_collection.find_one({'username': username}): 
            flash('Email already exists')
            return redirect(url_for('tambah_data_admin'))
        
        new_user = {
            'username': username,
            'password': hash_password
        }

        user_id = dataAdmin_collection.insert_one(new_user).inserted_id
        set_login_time()
        session['user_id'] = str(user_id)
        session['fullname'] = username
        return redirect(url_for('admin_data_akun'))
    
@app.route('/hapusDataAdmin/<string:_id>', methods=["GET", "POST"])
def delete_data_admin(_id):
    db.dataAdmin.delete_one({'_id': ObjectId(_id)})
    return redirect(url_for('admin_data_akun'))

@app.route('/adminDataPemesanan')
def admin_data_pemesanan():
    dataPemesanan = list(db.payments.find({}))
    return render_template('adminDataPemesanan.html', dataPemesanan=dataPemesanan)

# Fungsi untuk membuat laporan PDF
def create_pdf(riwayat_pemesanan):
    buffer = BytesIO()  # Buat BytesIO untuk menyimpan PDF sementara di memori
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))  # Set pagesize to landscape
    
    # Membuat data laporan
    data = [
        ["Nama", "No.Hp", "Tanggal", "Waktu", "Harga", "Jenis", "Nama", "Jenis", "Metode", "Bukti"]
    ]
    
    for pemesanan in riwayat_pemesanan:
        # Memeriksa panjang teks dan memotongnya jika terlalu panjang
        fullname = pemesanan.get("fullname", "")[:20]  # Memotong nama jika lebih dari 20 karakter
        phone_number = pemesanan.get("phone_number", "")[:15]  # Memotong nomor telepon jika lebih dari 15 karakter
        selected_date = pemesanan.get("selected_date", "")
        selected_time = pemesanan.get("selected_time", "")
        selected_price = pemesanan.get("selected_price", "")
        selected_sport = pemesanan.get("selected_sport", "")
        selected_court = pemesanan.get("selected_court", "")
        payment_type = pemesanan.get("payment_type", "")
        payment_method = pemesanan.get("payment_method", "")
        payment_proof = "Ada" if pemesanan.get("payment_proof") else "Tidak ada"
        
        data.append([
            fullname,
            phone_number,
            selected_date,
            selected_time,
            selected_price,
            selected_sport,
            selected_court,
            payment_type,
            payment_method,
            payment_proof
        ])
    
    # Membuat tabel
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Set teks ke tengah vertikal untuk semua sel
        ('WORDWRAP', (0, 0), (-1, -1), True),  # Aktifkan wrap untuk semua sel
        ('LEFTPADDING', (0, 0), (-1, -1), 5),  # Atur padding kiri untuk membuat ruang antara teks dan tepi sel
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),  # Atur padding kanan
        ('TOPPADDING', (0, 0), (-1, -1), 5),  # Atur padding atas
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5)  # Atur padding bawah
    ]))
    
    # Set margin untuk memperbesar area tampilan data
    doc.pagesize = landscape(letter)
    doc.title = "Laporan Pemesanan"
    doc.topMargin = 30
    doc.bottomMargin = 30
    doc.leftMargin = 50  # Perbesar margin kiri
    doc.rightMargin = 50  # Perbesar margin kanan
    doc.build([table])
    
    pdf_bytes = buffer.getvalue()  # Dapatkan konten PDF dari BytesIO
    buffer.close()  # Tutup BytesIO
    
    return pdf_bytes

@app.route('/adminRiwayatPemesanan', methods=['GET'])
def admin_riwayat_pemesanan():
    riwayat_pemesanan = list(db.riwayatPemesanan.find())
    return render_template('adminRiwayatPemesanan.html', riwayatPemesanan=riwayat_pemesanan)

# Rute untuk membuat laporan PDF
@app.route('/buatLaporanPemesanan', methods=['GET'])
def buat_laporan_pemesanan():
    tanggal_str = request.args.get('tanggal')
    if tanggal_str:
        tanggal = datetime.strptime(tanggal_str, '%d-%m-%Y').date()
        start_date = datetime.combine(tanggal, datetime.min.time())
        end_date = datetime.combine(tanggal, datetime.max.time())
        # Ambil data riwayat pemesanan berdasarkan rentang tanggal
        riwayat_pemesanan = list(db.riwayatPemesanan.find({"selected_date": {"$gte": start_date, "$lte": end_date}}))
    else:
        # Ambil semua data riwayat pemesanan jika tanggal tidak diberikan
        riwayat_pemesanan = list(db.riwayatPemesanan.find())
    
    # Buat laporan PDF dari data yang ditemukan
    pdf_bytes = create_pdf(riwayat_pemesanan)
    
    # Buat respons HTTP dengan laporan PDF sebagai attachment
    response = make_response(pdf_bytes)
    response.headers['Content-Disposition'] = 'attachment; filename=laporan_pemesanan.pdf'
    response.headers['Content-Type'] = 'application/pdf'
    
    return response

@app.route('/hapusSemuaDataRiwayatPemesanan', methods=["GET", "POST"])
def delete_all_data_pemesanan():
    db.riwayatPemesanan.delete_many({})
    return redirect(url_for('admin_riwayat_pemesanan'))

@app.route('/selesaikan-pesanan/<string:_id>', methods=['POST'])
def selesaikan_pemesanan(_id):
    try:
        # Cari pesanan dari database payments
        payment = db.payments.find_one_and_delete({"_id": ObjectId(_id)})
        if payment:
            # Jika ditemukan, simpan ke riwayatPemesanan
            db.riwayatPemesanan.insert_one(payment)
            return jsonify({"success": True}), 200
        else:
            return jsonify({"success": False, "error": "Pesanan tidak ditemukan"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/galeri', methods=['GET', 'POST'])
def galeri():
    dataGaleri = list(db.dataGaleri.find({}))
    return render_template('adminGaleri.html', dataGaleri=dataGaleri)

@app.route('/tambahDataGaleri', methods=['GET', 'POST'])
def tambah_data_galeri():
    if request.method == 'POST':
        judul_foto = request.form['judul_foto']
        foto_lapangan = request.files['foto_lapangan']
        
        if foto_lapangan:
            nama_file_asli = foto_lapangan.filename
            nama_file_foto = secure_filename(nama_file_asli)
            file_path = f'./static/img/{nama_file_foto}'
            foto_lapangan.save(file_path)
        else:
            nama_file_foto = None
            
        dataGaleri_collection.insert_one({
            'judul': judul_foto,
            'foto': nama_file_foto
        })
        
        return redirect(url_for("galeri"))
        
    return render_template('tambahDataGaleri.html')

@app.route('/editDataGaleri/<string:_id>', methods=["GET", "POST"])
def edit_data_galeri(_id):
    if request.method == 'POST':
        judul_foto = request.form['judul_foto']
        foto_lapangan = request.files['foto_lapangan']
        
        if foto_lapangan:
            nama_file_asli = foto_lapangan.filename
            nama_file_foto = secure_filename(nama_file_asli)
            file_path = f'./static/img/{nama_file_foto}'
            foto_lapangan.save(file_path)
            
            db.dataGaleri.update_one({'_id': ObjectId(_id)}, {'$set': {
                'judul': judul_foto,
                'foto': nama_file_foto
            }})
        else:
            db.dataGaleri.update_one({'_id': ObjectId(_id)}, {'$set': {
                'judul': judul_foto
            }})
        
        return redirect(url_for('galeri'))
    return render_template('tambahDataGaleri.html')

@app.route('/hapusDataGaleri/<string:_id>', methods=["GET", "POST"])
def delete_data_galeri(_id):
    db.dataGaleri.delete_one({'_id': ObjectId(_id)})
    return redirect(url_for('galeri'))

@app.route('/userReviewLapangan')
def user_review_lapangan():
    fullname = session.get('fullname') 
    email = session.get('email')
    current_date_time = datetime.now().strftime('%A, %d %B %Y')
    check_login_time()
    return render_template('reviewLapangan.html', fullname=fullname, email=email, current_date_time=current_date_time)

@app.route('/submitReview', methods=['POST'])
def submit_review():
    if request.method == 'POST':
        # Ambil data dari formulir
        nama = request.form['nama']
        email = request.form['email']
        ulasan = request.form['ulasan']
        tanggal = request.form['tanggal']
        foto = request.files.get('foto')

        # Inisialisasi nama_file_foto
        nama_file_foto = None

        if foto:
            nama_file_asli = foto.filename
            nama_file_foto = secure_filename(nama_file_asli)
            file_path = os.path.join('static', 'img', nama_file_foto)
            foto.save(file_path)

        # Simpan data ke dalam MongoDB
        doc = {
            'nama': nama,
            'email': email,
            'foto': nama_file_foto,  # Tetap gunakan nama_file_foto di sini
            'ulasan': ulasan,
            'tanggal': tanggal
        }
        dataReview_collection.insert_one(doc)

        # Redirect ke halaman setelah submit
        return redirect(url_for('user_review_lapangan'))

@app.route('/adminDataUser', methods=['GET'])
def admin_data_user():
    users = list(users_collection.find({}))
    return render_template('adminDataUser.html', users=users)

@app.route('/tambahDataPelanggan', methods=['GET', 'POST'])
def tambah_data_pelanggan():
    if request.method == 'GET':
        return render_template('tambahDataPelanggan.html')
    else:
        fullname = request.form['fullname']
        phone_number = request.form['phone_number']
        email = request.form['email']
        password1 = request.form['password1'].encode('utf-8')
        password2 = request.form['password2'].encode('utf-8')
        hash_password = bcrypt.hashpw(password1, bcrypt.gensalt())
        
        if not fullname or not phone_number or not email or not password1 or not password2:
            flash('Please fill in all fields')
            return redirect(url_for('tambah_data_pelanggan'))
        
        if len(password1) < 8:
            flash('Password must be at least 8 characters long')
            return redirect(url_for('tambah_data_pelanggan'))
        
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            flash('Invalid email address')
            return redirect(url_for('tambah_data_pelanggan'))
        
        if not re.match(r'^\+?1?\d{9,15}$', phone_number):
            flash('Invalid phone number')
            return redirect(url_for('tambah_data_pelanggan'))

        if password1 != password2:
            flash('Passwords do not match')
            return redirect(url_for('tambah_data_pelanggan'))

        if users_collection.find_one({'email': email}): 
            flash('Email already exists')
            return redirect(url_for('tambah_data_pelanggan'))
        
        new_user = {
            'fullname': fullname,
            'phone_number': phone_number,
            'email': email,
            'password': hash_password
        }

        user_id = users_collection.insert_one(new_user).inserted_id
        set_login_time()
        session['user_id'] = str(user_id)
        session['email'] = email
        session['fullname'] = fullname
        session['phone_number'] = phone_number
        return redirect(url_for('admin_data_user'))

@app.route('/hapusDataPelanggan/<string:_id>', methods=["GET", "POST"])
def delete_data_pelanggan(_id):
    db.users.delete_one({'_id': ObjectId(_id)})
    return redirect(url_for('admin_data_user'))

@app.route('/adminPembayaran', methods=['GET'])
def admin_pembayaran():
    pembayaran = list(dataPembayaran_collection.find({}))
    return render_template('adminPembayaran.html', pembayaran=pembayaran)

@app.route('/tambahDataPembayaran', methods=['GET', 'POST'])
def tambah_data_pembayaran():
    if request.method == 'POST':
        jenis_pembayaran = request.form['jenis_pembayaran']
        nomor_pembayaran = request.form['nomor_pembayaran']
            
        dataPembayaran_collection.insert_one({
            'jenis_pembayaran': jenis_pembayaran,
            'nomor_pembayaran': nomor_pembayaran
        })
        
        return redirect(url_for("admin_pembayaran"))
        
    return render_template('tambahDataPembayaran.html')

@app.route('/hapusDataPembayaran/<string:_id>', methods=["GET", "POST"])
def delete_data_pembayaran(_id):
    db.dataPembayaran.delete_one({'_id': ObjectId(_id)})
    return redirect(url_for('admin_pembayaran'))

@app.route('/editDataPembayaran/<string:_id>', methods=["GET", "POST"])
def edit_data_pembayaran(_id):
    if request.method == 'POST':
        jenis_pembayaran = request.form['jenis_pembayaran']
        nomor_pembayaran = request.form['nomor_pembayaran']
        
        db.dataPembayaran.update_one({'_id': ObjectId(_id)}, {'$set': {
            'jenis_pembayaran': jenis_pembayaran,
            'nomor_pembayaran': nomor_pembayaran
        }})
        
        return redirect(url_for('admin_pembayaran'))
    return render_template('tambahDataPembayaran.html')


# LOGIN SEBAGAI ADMIN
@app.route('/adminLogin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = dataAdmin_collection.find_one({'username': username})

        if user is not None and len(user) > 0:
            if bcrypt.checkpw(password.encode('utf-8'), user['password']):
                user_obj = User()
                user_obj.id = str(user['_id'])
                login_user(user_obj)
                
                return redirect(url_for('admin_data_lapangan'))
            
            else:
                flash("Invalid email or password")
                return redirect(url_for('admin_login'))
            
        else:
            flash("Invalid email or password")
            return redirect(url_for('admin_login'))
        
    else:
        return render_template('adminLogin.html')
    
@app.route('/adminLogout')
def admin_logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
