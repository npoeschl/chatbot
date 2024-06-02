import mysql.connector
import dbcredentials

def queryWrapper(func):
    def inner(*args,**kwargs):
        global conn
        global cur
        conn = getConnection()
        cur = getSQLCursor(conn)
        return func(*args,**kwargs)
    return inner 
      

def getConnection():
    try:
       conn = mysql.connector.connect(
          user=dbcredentials.user,
          password=dbcredentials.password,
          host=dbcredentials.host,
          port=dbcredentials.port,
          database=dbcredentials.database,
          autocommit = True)
    except mysql.connector.Error as e:
       print(f"Error connecting to mysql.connector Platform: {e}")

    return conn

def getSQLCursor(conn):
    cur = conn.cursor()
    return cur

@queryWrapper
def isValidUser(userId):
    cur.execute("SELECT 1 FROM users WHERE user_id = '"+str(userId)+"'")
    result = cur.fetchall()
    return result

@queryWrapper
def getAllActiveContracts():
    cur.execute("SELECT contract_id, contract_start, contract_end, contract_next_cancellation_date, notice_period_months, contract_renewal_period_months " +
                 "FROM contracts WHERE is_active = 1")
    result = cur.fetchall()
    return result

@queryWrapper
def deleteContractById(Id):
    try:
        cur.execute("DELETE FROM contracts WHERE contract_id = '"+str(Id)+"'")
    except mysql.connector.Error as e:
        print(f"Error while trying to delete: {e}")   

@queryWrapper
def getActiveContractCategories():
    cur.execute("SELECT DISTINCT contract_categories.contract_category_id, contract_categories.contract_category " + 
                "FROM contracts JOIN contract_types ON contracts.contract_type = contract_types.contract_type_id " + 
                "JOIN contract_categories ON contract_types.contract_category = contract_categories.contract_category_id WHERE contracts.is_active = 1")
    result = cur.fetchall()
    return result

@queryWrapper
def getContractCategories():
    cur.execute("SELECT * FROM contract_categories")
    result = cur.fetchall()
    return result

@queryWrapper
def getContractTypes(category):
    cur.execute("SELECT contract_types.contract_type_id, contract_types.contract_type FROM contract_types " + 
                "JOIN contract_categories ON contract_types.contract_category = contract_categories.contract_category_id " + 
                "WHERE contract_categories.contract_category_id = '"+category+"'")
    result = cur.fetchall()
    return result

@queryWrapper
def getAllContracts():
    cur.execute("SELECT * FROM contracts JOIN contract_types ON contracts.contract_type = contract_types.contract_type_id " + 
                "JOIN contractors ON contractors.contractor_id = contracts.contractor")
    result = cur.fetchall()
    return result

@queryWrapper
def getContracts(type):
    cur.execute("SELECT * FROM contracts JOIN contract_types ON contracts.contract_type = contract_types.contract_type_id " + 
                "JOIN contractors ON contractors.contractor_id = contracts.contractor WHERE contract_types.contract_type_id = '"+type+"'")
    result = cur.fetchall()
    return result

@queryWrapper
def getBeneficiaries():
    cur.execute("SELECT * FROM contract_beneficiaries")
    result = cur.fetchall()
    return result

@queryWrapper
def getContractors():
    cur.execute("SELECT contractor_id, contractor_name FROM contractors ORDER BY contractor_name")
    result = cur.fetchall()
    return result

@queryWrapper
def getPeriods():
    cur.execute("SELECT * FROM payment_periods")
    result = cur.fetchall()
    return result    

@queryWrapper
def getAccounts():
    cur.execute("SELECT * FROM bankaccounts")
    result = cur.fetchall()   
    return result  

@queryWrapper
def getContractById(id):
    cur.execute("SELECT contract_id, contract_fee, name, period_name, contractor_name, contract_types.contract_type, bankaccounts.account_IBAN," + 
                "contract_next_cancellation_date FROM contracts JOIN contract_types ON contracts.contract_type = contract_types.contract_type_id " + 
                "JOIN contract_beneficiaries ON contract_beneficiaries.id = contracts.contract_beneficiary_1 " + 
                "JOIN payment_periods ON payment_periods.period_id = contracts.contract_payment_period " + 
                "JOIN contractors ON contractors.contractor_id = contracts.contractor JOIN bankaccounts ON bankaccounts.account_id = contracts.bankaccount " + 
                "WHERE contracts.contract_id = '"+str(id)+"'")
    result = cur.fetchone()
    return result

@queryWrapper
def saveContract(data):
    for key, value in data.items():
        print(key, ":", value)

    try: cur.execute("INSERT INTO contracts(user_id, contract_type, contract_beneficiary_1, contractor, contract_fee, contract_payment_period, bankaccount, notice_period_months," + 
                "contract_start, contract_end, contract_next_cancellation_date, contract_renewal_period_months) " + 
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s); SELECT LAST_INSERT_ID();", (data['userid'],
                                                                data['type'],
                                                                data['beneficiary'],
                                                                data['contractor'],
                                                                data['fee'],
                                                                data['period'],
                                                                data['account'],
                                                                data['noticeperiod'],
                                                                data['startdate'],
                                                                data['enddate'],
                                                                data['nextcancellationdate'],
                                                                data['renewalperiod']))
    
    except mysql.connector.Error as e:
        print(f"Error while inserting contract: {e}") 
    result = cur.fetchone()
    return result

@queryWrapper
def newCategory(categoryName):
   cur.execute("INSERT INTO contract_categories SET contract_category = '"+categoryName+"'")
   cur.execute("SELECT MAX(contract_category_id) FROM contract_categories")
   result = cur.fetchone()
   return result

@queryWrapper
def newType(categoryID, typeName):
   cur.execute("INSERT INTO contract_types(contract_type, contract_category) VALUES (?, ?)", (typeName, categoryID))
   cur.execute("SELECT MAX(contract_type_id) FROM contract_types")
   result = cur.fetchone()   
   return result

@queryWrapper
def updateContractDates(data):
    executestring = "UPDATE contracts SET contract_end = '"+data[1]+"', contract_next_cancellation_date = '"+data[2]+"' WHERE contract_id = " +str(data[0])+" "
    cur.execute(executestring)

@queryWrapper
def setContractAlertingStatus(contractId: int, alertingStatus: int):
    """Set Alertings Status of contract to 1 or 0"""
    print("setting alertingstatus of contract: "+str(contractId)+" to: "+str(alertingStatus))
    try: cur.execute("UPDATE contracts SET alert_active = '"+str(alertingStatus)+"' WHERE contract_id = '"+str(contractId)+"'")
    except mysql.connector.Error as e:
        print("Something went wrong while updating the alerting status of the contract: {}".format(e))