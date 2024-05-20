import contract_dbqueries
from datetime import datetime
from dateutil.relativedelta import relativedelta

#Get all contracts (that are still active)
def checkDates():
    contracts= contract_dbqueries.getAllActiveContracts()
    #print(contracts)
    now =  datetime.now().date()

    for c in contracts:
        enddate = datetime.strptime(str(c[2]), '%Y-%m-%d').date()
        
        nextcanceldate = datetime.strptime(str(c[3]), '%Y-%m-%d').date()
        
        if(now > nextcanceldate):
            #Vertrag wurde automatisch verlängert
            renewalperiod = int(c[5])
            newenddate = enddate + relativedelta(months=+renewalperiod) 
            newnextcanceldate = nextcanceldate + relativedelta(months=+renewalperiod)
            newenddatestring = str(newenddate)
            newnextcanceldatestring = str(newnextcanceldate)
            data = []
            data.append(c[0])
            data.append(newenddatestring)
            data.append(newnextcanceldatestring)
            contract_dbqueries.updateContractDates(data)
        
        else:
            #Ende der Vertragslaufzeit noch nicht erreicht
            continue

def main():
    checkDates()


if __name__ == "__main__":
    main()