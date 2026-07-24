from flask import Flask, render_template, redirect, url_for, request, make_response,flash

import jwt
from datetime import datetime, timedelta, timezone

from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename
import uuid

# ------------import database logics -------------------
from database.tables import createTables
from database.utility import checkUserExists, addUser, getUserDetails, getCatagoriesFromDB, getProductsFromDB
from database.utility import addProductToDB, totalOrdersCount, getOrders, usersDetails, getUserDetailsByID, updateAdminProfile
from database.utility import getProductDetailsByID, updateProductInfo, updateProductStatus, viewUserByAdmin, viewOrderDetails, totalProducts

app = Flask(__name__)
app.config['SECRET_KEY'] = "narasimha@123"



## -------------------------- Helper Functions ------------------------------------


## token protection decorator
def token_required(role=None):
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = request.cookies.get('token')

            if not token:
                return redirect(url_for('login'))

            try:
                data = jwt.decode(
                    token,
                    app.config['SECRET_KEY'],
                    algorithms=["HS256"]
                )
            except jwt.ExpiredSignatureError:
                return redirect(url_for('login'))
            except jwt.InvalidTokenError:
                return redirect(url_for('login'))

            if role and data['role'] != role:
                return "Unauthorized access"

            return f(*args, **kwargs)
        return decorated
    return wrapper


def getUserByToken():
    token = request.cookies.get('token')

    if not token:
        return None

    try:
        data = jwt.decode(
            token,
            app.config['SECRET_KEY'],
            algorithms=["HS256"]
        )

        userid = data.get('userid')
        role = data.get('role')

        user = getUserDetailsByID(userid=userid)

        return user

    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None



# index route
@app.route('/')
def index():
    return render_template('user/user_home.html',
                            user_logged_in=False)


# login route
@app.route("/login", methods=['GET',"POST"])
def login():
    # if it is POST request method
    # get form data
    if request.method == 'POST':
        username = request.form['email']
        password = request.form['password']
       
        # user validation
        data = getUserDetails(email=username)
        # print(data)
        if data and check_password_hash(data['password'], password):
            
            # create login token
            # utc_now = datetime.now(timezone.utc)

            # Add 2 hours
            exp_time = datetime.now(timezone.utc) + timedelta(hours=2)

            token = jwt.encode(
                {
                    "userid": data["userid"],
                    "role": data["role"],
                    "exp": exp_time,
                    "username":data['name']
                },
                app.config['SECRET_KEY'],
                algorithm="HS256"
            )

             # Based on role it selects the user dashbord or admin dashboard
            response = make_response(
                redirect(url_for('admin' if data['role']=='admin' else 'user'))
            )

            # store token in cookie
            response.set_cookie(
                'token',
                token,
                httponly=True,
                secure=False  # True in production (HTTPS)
            )

            return response
        # If credintial is incorrect
        flash('User Credentials incorrect')
        return redirect(url_for('login'))

    # if it is get request 
    return render_template('auth/login.html')


# ---------------------- images upload path ------------------
PROFILE_UPLOAD_FOLDER = 'static/uploads/profile'
PRODUCT_UPLOAD_FOLDER = 'static/uploads/products'

app.config['PROFILE_UPLOAD_FOLDER'] = os.path.join('static', 'uploads', 'profiles')
app.config['PRODUCT_UPLOAD_FOLDER'] = os.path.join('static', 'uploads', 'products')
os.makedirs(app.config['PRODUCT_UPLOAD_FOLDER'], exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}



def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
# ------------------------------------------------------------
#registe Route
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        profile_image = request.files.get('profile_image')

        # basic validation
        if not name or not email or not phone or not password:
            flash("All required fields must be filled")
            return redirect(url_for('register'))

        # check user already exists
        if checkUserExists(email=email):
            flash("Email already registered")
            return redirect(url_for('register'))

        # password hash
        hashed_password = generate_password_hash(password)

        # handle profile image
        image_path = None
        if profile_image and profile_image.filename != "":
            if allowed_file(profile_image.filename):
                filename = secure_filename(profile_image.filename)
                os.makedirs(app.config['PROFILE_UPLOAD_FOLDER'], exist_ok=True)

                image_path = os.path.join(
                    app.config['PROFILE_UPLOAD_FOLDER'],
                    filename
                )

                profile_image.save(image_path)
            else:
                flash("Invalid image format")
                return redirect(url_for('register'))

        # add user to database
        addUser(
            name=name,
            email=email,
            phone_number=phone,
            password=hashed_password,
            profile_image=image_path
        )

        flash("Registration successful. Please login.")
        return redirect(url_for('login'))

    return render_template('auth/register.html')

# forgotpassword route
@app.route('/forgotpassword')
def forgotpassword():
    return "forgot Password Page"



## Admin Routes
# admin dashborad route
@app.route('/admin')
@token_required(role='admin')
def admin():

    total_products = totalProducts() # need to update in utilituy
    total_orders = totalOrdersCount()
    pending_orders = totalOrdersCount(status="PENDING") # need to update in utilituy
    total_users = len(usersDetails()) # need to update in utilituy
    return render_template('admin/dashboard.html',
                            total_products=total_products,
                            total_orders=total_orders,
                            pending_orders=pending_orders,
                            total_users=total_users
                        )

# product route

@app.route('/admin/products')
@token_required(role='admin')
def adminproducts():
    # get all categories name 
    categories = getCatagoriesFromDB()

    product_name = request.args.get('name',"")
    category = request.args.get('category', "")
    status = request.args.get('status', "")

    # print(category, product_name, status)
    # Get all products from  database
    products = getProductsFromDB(name=product_name, category= category, status= status)
    # print(products)
    return render_template('admin/products.html', categories= categories, products=products)

# Add product Route

@app.route('/admin/addproduct', methods = ['GET','POST'])
@token_required(role='admin')
def adminaddproduct():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        category = request.form['category']
        active = request.form['active']
        price = request.form['price']
        stock = request.form['stock']
        image = request.files.get('image')
        new_category = request.form.get('new_category')
        # check if new category is avialable or not 
        # if new_category:
        #     category = new_category
        if category == "new" and new_category:
            category = new_category
        # print("******************************")
        # print("--------- DEBUG START ---------")
        # print("request.files:", request.files)
        # print("image object:", image)
        # print("image filename:", image.filename if image else "NO IMAGE")
        # print("PRODUCT_UPLOAD_FOLDER:", app.config.get('PRODUCT_UPLOAD_FOLDER'))
        # print("--------------------------------")

        image_path = None


        if image and image.filename != '':

            ext = image.filename.rsplit('.', 1)[1].lower()

            if ext in ALLOWED_EXTENSIONS:

                filename = str(uuid.uuid4()) + "_" + secure_filename(image.filename)
                print(filename)
                save_path = os.path.join(
                    app.config['PRODUCT_UPLOAD_FOLDER'],
                    filename
                )
                print(save_path)
                image.save(save_path)
                print("saved")
                # Save relative path in DB
                image_path = f"uploads/products/{filename}"

        
        # add procuts details into products table
        addProductToDB(name=name,
                       description=description,
                       category=category,
                       price=price,
                       stock=stock,
                       active=active,
                       image_url=image_path)
        flash("Product added successfully","success")
        return redirect(url_for('adminproducts')) # after redirect to products page

    return render_template('admin/addproduct.html', categories = getCatagoriesFromDB())


@app.route('/admin/editproduct/<int:productid>', methods=['GET', 'POST'])
@token_required(role='admin')
def editproduct(productid):
    # get product data from database
    product = getProductDetailsByID(productid=productid)
    # if request is post 
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        category = request.form.get('category')
        price = request.form.get('price')
        stock = request.form.get('stock')
        active = request.form.get('active')
        # update with new data in database
        if updateProductInfo(name, description,category, price, stock, active, productid):
            flash("Product updated successfully", "success")
            return redirect(url_for('adminproducts'))
        flash("Product NoT updated", "Error")
        return redirect(url_for('adminproducts'))

    return render_template('admin/edit_product.html',product = product)

# deactivate user
# view user 
@app.route('/admin/deactivate_product/<int:productid>', methods=['POST'])
@token_required(role='admin')
def deactivate_product(productid):
    # update in database
    status = updateProductStatus(productid=productid, status=0)
    if status:
        flash("Product deactivated successfully", "warning")
        return redirect(url_for('adminproducts'))
    flash("Product Not deactivated", "Error")
    return redirect(url_for('adminproducts'))
    
@app.route('/admin/activate_product/<int:productid>', methods=['POST'])
@token_required(role='admin')
def activate_product(productid):
    # update in database
    status = updateProductStatus(productid=productid, status=1)
    if status:
        flash("Product Activates successfully", "warning")
        return redirect(url_for('adminproducts'))
    flash("Product Not activated", "Error")
    return redirect(url_for('adminproducts'))
    

@app.route('/admin/users')
@token_required(role='admin')
def adminusers():

    # filters
    name = request.args.get('name', '').strip()
    email = request.args.get('email', '').strip()
    role = request.args.get('role', '').strip()
    users = usersDetails(name=name, email=email, role=role)
    

    return render_template(
        "admin/users.html",
        users=users,
        total_users=len(users)
    )


# orders Route

@app.route('/admin/orders')
@token_required(role='admin')
def adminorders():
    # get filter parameter 
    orderid = request.args.get('orderid',"")
    product_name = request.args.get('productname',"")
    from_date = request.args.get('fromdate',"")
    to_date = request.args.get('todate',"")

    orders_count = totalOrdersCount()
    # getting filterd orders
    orders = getOrders(orderid=orderid,
                       product_name=product_name,
                       from_date=from_date,
                       to_date=to_date)
    filter_orders_count = len(orders)
    # print(orders[:3])

    return render_template('admin/orders.html',
                            total_orders = orders_count,
                            filtred_order_count=filter_orders_count,
                            orders=orders)


# view order
@app.route('/admin/view-Order/<int:order_id>', methods=['GET', 'POST'])
@token_required(role='admin')
def view_order(order_id):
    order, items = viewOrderDetails(order_id)

    return render_template(
        'admin/view_order.html',
        order=order,
        items=items
    )
# view user 
@app.route('/admin/viewuser/<int:userid>', methods=['GET', 'POST'])
@token_required(role='admin')
def view_user(userid):

    # get user data from database
    user = viewUserByAdmin(userid=userid)
    if not user:
        flash("User not found", "danger")
        return redirect(url_for('adminusers'))

    return render_template('admin/view_user.html',user=user
    )
    

# deactivate user
# view user 
@app.route('/admin/deactivate/<int:userid>', methods=['GET', 'POST'])
@token_required(role='admin')
def deactivate_user(userid):
    return "deactivate user"


# admin profile route

@app.route('/admin/profile', methods=['GET', 'POST'])
@token_required(role='admin')
def adminprofile():

    user = getUserByToken()   # helper → decodes token, returns user data

    if request.method == 'POST':

        name = request.form.get('name')
        phone = request.form.get('phone')

        updateAdminProfile(
            userid=user['userid'],
            name=name,
            phone=phone
        )

        flash("Profile updated successfully", "success")
        return redirect(url_for('adminprofile'))

    return render_template(
        'admin/profile.html',
        user=user
    )



@app.route('/admin/change-password', methods=['POST'])
def admin_change_password():
    user = getUserByToken()

    if not user or user['ROLE'] != 'admin':
        return redirect(url_for('login'))

    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')

    # Verify current password
    if not check_password_hash(user['PASSWORD'], current_password):
        return redirect(url_for('admin_profile'))

    hashed_password = generate_password_hash(new_password)

    
    # update admin profile in database
    updateAdminProfile(new_password=hashed_password, userid=user['PASSWORD'])

    return redirect(url_for('admin_profile'))



@app.route('/admin/logout')
def adminlogout():
    response = make_response(redirect(url_for('login')))

    # delete token cookie
    response.set_cookie(
        'token',
        '',
        expires=0,
        httponly=True
    )

    return response


# --------------------------------User Routes --------------------------------#

# get user utility database fuctions from database
from database.userUtility import getProductsByCategory, getProductById,getCartItem,increaseCartQuantity, insertCartItem
from database.userUtility import getUserCartItems, removeFromCart, updateCartQuantity, getProductsBasedOnSearch, getCartItems, placeOrder
from database.userUtility import myOrders


# helper fucntion 
def getDataFromToken():
    token = request.cookies.get('token')

    if not token:
        return redirect(url_for('login'))

    try:
        data = jwt.decode(
            token,
            app.config['SECRET_KEY'],
            algorithms=["HS256"]
        )
        return data
    except jwt.ExpiredSignatureError:
        return redirect(url_for('login'))
    except jwt.InvalidTokenError:
        return redirect(url_for('login'))
    

#User dashboard route

@app.route('/user')
@token_required(role='user')
def user():
    user = getUserByToken()
    name = user.get('NAME','Dear User')
    # print(user)
    return render_template('user/user_home.html',
                            user_logged_in=True,
                            username=name)

#User dashboard route

@app.route('/user/search')
@token_required(role='user')
def search():
    q = request.args.get('q', None)
    if q:
        products = getProductsBasedOnSearch(product_name=q)
        return render_template('user/category_products.html', products=products, category=q, user_logged_in=True,
)
    return render_template('user/user_home.html')


#home route
# @token_required(role='user')
# @app.route('/user/home')
# def user_home():
#     return "user home page"

@app.route('/category/<string:category_name>')
def category_products(category_name):
    user = getUserByToken()
    name = user.get('NAME','Dear User')

    # Get query parameters
    sort = request.args.get('sort')
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')

    
    products = getProductsByCategory(category_name, min_price, max_price,sort)
    return render_template('user/category_products.html', products=products, category=category_name,
                           user_logged_in=True, username=name)

# user product details 
@app.route('/user/products/<category>/<productid>')
def user_product_details(category_name, product_id):
    return "Product Info"
# categories route
@token_required(role='user')
@app.route('/user/categories')
def user_categories():
    return "User categories page"




@app.route('/add-to-cart', methods=['POST'])
@token_required(role='user')
def add_to_cart():
    # print(getDataFromToken())
    user = getDataFromToken()
    
    user_id = user['USERID']   # adjust if your token stores differently
    product_id = request.form.get('product_id')

    # Get product details
    product = getProductById(product_id)

    if not product:
        flash("Product not found", "danger")
        return redirect(request.referrer)

    # Check if already in cart
    existing = getCartItem(user_id, product_id)

    if existing:
        increaseCartQuantity(user_id, product_id)
    else:
        insertCartItem(user_id, product_id, product['PRICE'])

    flash("Added to cart successfully", "success")
    return redirect(request.referrer)


@app.route('/cart')
@token_required(role='user')
def view_cart():
    user = getUserByToken()
    name = user.get('NAME','Dear User')
    
    user_id = user['USERID']  # adjust if needed

    cart_items = getUserCartItems(user_id)

    # Calculate grand total
    grand_total = sum(item['TOTAL_PRICE'] for item in cart_items)

    return render_template(
        'user/cart.html',
        cart_items=cart_items,
        grand_total=grand_total,
        user_logged_in=True,
        username=name
    )

@app.route('/remove-from-cart', methods=['POST'])
@token_required(role='user')
def remove_from_cart():
    user = getUserByToken()
    name = user.get('NAME','Dear User')
    user_id = user['USERID']
    product_id = request.form.get('product_id')

    # delete produt from cart
    removeFromCart(user_id=user_id, product_id=product_id)

    flash("Item removed from cart", "success")
    return redirect(url_for('view_cart'))

@app.route('/update-cart-quantity', methods=['POST'])
@token_required(role='user')
def update_cart_quantity():
    user_data = getDataFromToken()
    user_id = user_data['userid']
    product_id = request.form.get('product_id')
    quantity = request.form.get('quantity')

    # update quantity
    updateCartQuantity(quantity=quantity, user_id=user_id, product_id=product_id)

    

    flash("Cart updated", "success")
    return redirect(url_for('view_cart'))


# users orders route
@token_required(role='user')
@app.route('/users/orders')
def user_orders():
    return "Users orders page"

# cart route
@token_required(role='user')
@app.route('/user/cart')
def user_cart():
    return "user cart page"


# -------------------place order related --------------------------
@app.route('/user/checkout')
@token_required(role='user')
def checkout():

    user = getUserByToken()   # from your token decorator
    name = user.get('NAME','Dear User')
    total_amount, cart_items = getCartItems(user['USERID'])

    return render_template(
        "user/checkout.html",
        cart_items=cart_items,
        total_amount=total_amount,
        username=name,
        user_logged_in=True

    )


@app.route('/user/place-order', methods=['POST'])
@token_required(role='user')
def place_order():

    user = getUserByToken()
    total_amount, cart_items = getCartItems(user['USERID'])

    fullname = request.form['fullname']
    phone = request.form['phone']
    address = request.form['address']
    city = request.form['city']
    pincode = request.form['pincode']

    status, msg = placeOrder(user['USERID'], fullname, phone, address, city, pincode, total_amount, cart_items)
    if not status:
        flash(message=msg)
        return redirect(url_for('view_cart'))
    
    msg =  """
        🎉 Order Placed Successfully!
    """
    flash(msg)
    return redirect(url_for('user'))

# @app.route('/user/order-success')
# @token_required(role='user')
# def order_success():
#     return

@app.route('/my-orders')
def my_orders():
    user = getUserByToken()
    name = user.get('NAME','Dear User')
    orders = myOrders(userid=user['USERID'])
    
    return render_template("user/my_orders.html", orders=orders,username=name, user_logged_in=True)




@app.route('/user/profile', methods=['GET', 'POST'])
@token_required(role='user')
def user_profile():

    user = getUserByToken()   # helper → decodes token, returns user data

    if request.method == 'POST':

        name = request.form.get('name')
        phone = request.form.get('phone')

        updateAdminProfile(
            userid=user['userid'],
            name=name,
            phone=phone
        )

        flash("Profile updated successfully", "success")
        return redirect(url_for('user_profile'))

    return render_template(
        'user/profile.html',
        user=user
    )


@app.route('/user/change-password', methods=['POST'])
@token_required(role='user')
def user_change_password():
    user = getUserByToken()

    

    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')

    # Verify current password
    if not check_password_hash(user['PASSWORD'], current_password):
        return redirect(url_for('user_profile'))

    hashed_password = generate_password_hash(new_password)

    
    # update admin profile in database
    updateAdminProfile(new_password=hashed_password, userid=user['PASSWORD'])

    return redirect(url_for('user_profile'))
@app.route('/user/logout')
def user_logout():
    response = make_response(redirect(url_for('login')))

    # delete token cookie
    response.set_cookie(
        'token',
        '',
        expires=0,
        httponly=True
    )

    return response

# main
if __name__ == "__main__":
    createTables()
    app.run(debug=True, port=5006)
    