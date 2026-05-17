import pyrebase

firebaseConfig = {
    "apiKey": "AIzaSyB8YY7HiPimpm_4E9pxUuID6DgZnl_WkAE",
    "authDomain": "YOUR_PROJECT_ID.firebaseapp.com",
    "databaseURL": "",
    "projectId": "YOUR_PROJECT_ID",
    "storageBucket": "YOUR_PROJECT_ID.appspot.com",
    "messagingSenderId": "YOUR_SENDER_ID",
    "appId": "YOUR_APP_ID"
}

firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()
