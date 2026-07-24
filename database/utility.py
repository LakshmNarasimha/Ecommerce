from database.connection import databaseConfig


# check user exists or not
def checkUserExists(email:str):
    # database accesss
    db_config = databaseConfig()
    cursor = db_config.cursor()
    cursor.execute('select userid from users where email=%s;', (email,))
    
    if cursor.fetchone():
        cursor.close()
        db_config.close()
        return True
    else:
        cursor.close()
        db_config.close()
        return False
    
# insert user data into db
def addUser(name: str, email: str, phone_number: str, password: str, profile_image: str = None):
    db = databaseConfig()
    cursor = db.cursor()

    query = """
        INSERT INTO users
        (NAME, EMAIL, PHONE_NUMBER, PASSWORD, PROFILE_IMAGE)
        VALUES (%s, %s, %s, %s, %s)
    """

    cursor.execute(query, (name, email, phone_number, password, profile_image))
    db.commit()
    cursor.close()
    db.close()

    

# get password and role form database
def getUserDetails(email:str, role:str=None):
    # database accesss
    db_config = databaseConfig()
    cursor = db_config.cursor(dictionary=True)
    user_details_query = "select userid,name, password, role from users where email = %s;"
    if role:
        user_details_query =  "select userid, password, role from users where email = %s and role = %s"
        cursor.execute(user_details_query, (email,role))
    else:
        cursor.execute(user_details_query, (email,))
    data = cursor.fetchone()
    cursor.close()
    db_config.close()
    return data

# get user details by id
def getUserDetailsByID(userid:int, role:str=None):
    # database accesss
    db_config = databaseConfig()
    cursor = db_config.cursor(dictionary=True)
    user_details_query = "select * from users where userid = %s;"
    
    cursor.execute(user_details_query, (userid,))
    user = cursor.fetchone()
    cursor.close()
    db_config.close()
    return user


## Get all categories from database
def getCatagoriesFromDB():
    db_config = databaseConfig()
    cursor = db_config.cursor()
    cursor.execute('select distinct(category) from products;')
    category_list = cursor.fetchall()
    for i in range(len(category_list)):
        category_list[i] = category_list[i][0]
    cursor.close()
    db_config.close()
    return category_list


## Get all products from database
def getProductsFromDB(name='', category='', status=''):
    db = databaseConfig()
    cursor = db.cursor(dictionary=True)
    query = "SELECT * FROM products WHERE 1=1"
    values = []
    # Filter by product name
    if name:
        query += " AND NAME LIKE %s" # "SELECT * FROM products WHERE 1=1 AND NAME LIKE %s"
        values.append(f"%{name}%")
    # Filter by category
    if category:
        
        query += " AND CATEGORY = %s"
        values.append(category)
        
    # Filter by status
    if status:
        query += " AND ACTIVE = %s"
        values.append(status)
    cursor.execute(query, values)
    products = cursor.fetchall()
    # print(products[:5])
    cursor.close()
    db.close()
    return products




def addProductToDB(name, description, category, price, stock, active, image_url):
    db = databaseConfig()
    cursor = db.cursor()

    product_insert_query = """
        INSERT INTO products
        (NAME, DEScrIPTION, CATEGORY, PRICE, STOCK, ACTIVE, IMAGE_URL)
        VALUES (%s,%s,%s,%s,%s,%s, %s)
    """

    cursor.execute(product_insert_query, (name, description, category,price, stock, active, image_url))

    db.commit()
    cursor.close()
    db.close()


## Total Orders
def totalOrdersCount(status:str=None):
    db = databaseConfig()
    cursor = db.cursor()
    if status:
        cursor.execute("SELECT COUNT(*) FROM ORDERS where ORDERSTATUS not like %s;", ("DELIVERED",))
        
    else:
        cursor.execute("SELECT COUNT(*) FROM ORDERS;")
    orders_count = cursor.fetchone()[0]
    cursor.close()
    db.close()
    return orders_count

# get orders 
def getOrders(orderid="", product_name="", from_date="", to_date=""):

    db = databaseConfig()
    cursor = db.cursor(dictionary=True)

    query = """
        SELECT 
            o.ORDERID AS ORDER_ID,
            o.USERID AS USER_ID,
            o.CREATED_AT,
            o.ORDERSTATUS AS ORDER_STATUS,

            oi.PRODUCTNAME AS PRODUCT_NAME,
            oi.TOTALPRICE AS TOTAL_PRICE

        FROM ORDERS o
        JOIN ORDER_ITEMS oi ON o.ORDERID = oi.ORDERID
        WHERE 1=1
    """

    params = []

    # 🔍 Filter by Order ID
    if orderid:
        query += " AND o.ORDERID = %s"
        params.append(orderid)

    # 🔍 Filter by Product Name
    if product_name:
        query += " AND oi.PRODUCTNAME LIKE %s"
        params.append(f"%{product_name}%")

    # 🔍 Filter by Date Range
    if from_date:
        query += " AND DATE(o.CREATED_AT) >= %s"
        params.append(from_date)

    if to_date:
        query += " AND DATE(o.CREATED_AT) <= %s"
        params.append(to_date)

    query += " ORDER BY o.CREATED_AT DESC"

    cursor.execute(query, tuple(params))
    orders = cursor.fetchall()

    cursor.close()
    db.close()

    return orders


def toggleProduct(pid, status):
    db = databaseConfig()
    cursor = db.cursor()

    cursor.execute(
        "UPDATE products SET ACTIVE=%s WHERE PRODUCTID=%s",
        (status, pid)
    )

    db.commit()
    cursor.close()
    db.close()


# get users info 
def usersDetails(name:str="", email:str="",role:str=''):
    db = databaseConfig()
    cursor = db.cursor(dictionary=True)

    query = "SELECT USERID, NAME, EMAIL, PHONE_NUMBER, ROLE, CREATED_AT, PROFILE_IMAGE FROM USERS WHERE 1=1"
    values = []

    if name:
        query += " AND NAME LIKE %s"
        values.append(f"%{name}%")

    if email:
        query += " AND EMAIL LIKE %s"
        values.append(f"%{email}%")

    if role:
        query += " AND ROLE = %s"
        values.append(role)

    query += " ORDER BY CREATED_AT DESC"

    cursor.execute(query, values)
    users = cursor.fetchall()

    cursor.close()
    db.close()
    return users


# update admin profile in database
def updateAdminProfile(new_password:str,userid:int):
    db = databaseConfig()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
            UPDATE USERS
            SET PASSWORD=%s
            WHERE USERID=%s
        """, (new_password, userid))
    db.commit()
    cursor.close()
    db.close()



# get product details bt id
def getProductDetailsByID(productid:int):
    db = databaseConfig()
    cursor = db.cursor(dictionary=True)

    # FETCH PRODUCT
    cursor.execute(
        "SELECT * FROM products WHERE PRODUCTID = %s",
        (productid,)
    )
    product = cursor.fetchone()
    return product

# update product info in database
def updateProductInfo(name, description, category,price, stock, active, productid):
    db = databaseConfig()
    cursor = db.cursor(dictionary=True)
    update_query = """
            UPDATE products SET NAME=%s, DESCRIPTION=%s, CATEGORY=%s, PRICE=%s, STOCK=%s, ACTIVE=%s
            WHERE PRODUCTID=%s;
        """

    cursor.execute(update_query, (name, description, category,price, stock, active, productid))
    db.commit()
    return True

## Deactivate product in database
def updateProductStatus(productid, status:int=0):
    db = databaseConfig()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE products SET ACTIVE = %s WHERE PRODUCTID = %s",
        (status, productid)
    )
    db.commit()
    cursor.close()
    db.close()
    return True



## get view user
def viewUserByAdmin(userid):
    db = databaseConfig()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT USERID, NAME, EMAIL, ROLE, STATUS, CREATED_AT "
        "FROM users WHERE USERID = %s",
        (userid,)
    )

    user = cursor.fetchone()

    cursor.close()
    db.close()
    return user



# view order
def viewOrderDetails(order_id):
    db = databaseConfig()
    cursor = db.cursor(dictionary=True)

    #  Get Order Main Details
    cursor.execute("""
        SELECT *
        FROM ORDERS
        WHERE ORDERID = %s
    """, (order_id,))

    order = cursor.fetchone()

    if not order:
        cursor.close()
        db.close()
        return "Order not found"

    #  Get Order Items
    cursor.execute("""
        SELECT PRODUCTNAME,
               PRODUCTPRICE,
               QUANTITY,
               TOTALPRICE
        FROM ORDER_ITEMS
        WHERE ORDERID = %s
    """, (order_id,))

    items = cursor.fetchall()

    cursor.close()
    db.close()
    return order, items

def totalProducts():
    db = databaseConfig()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM PRODUCTS;")
    return cursor.fetchone()[0]