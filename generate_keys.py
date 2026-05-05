import streamlit_authenticator as stauth

# 1. Initialize the Hasher
hasher = stauth.Hasher()


your_password = "abcdefgh" # <-- CHANGE THIS

# 3. Use the .hash() method to hash the password
hashed_password = hasher.hash(your_password)

# 4. Print the result
print(hashed_password)