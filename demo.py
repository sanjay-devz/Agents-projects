import streamlit as st

# st.title("My web page!") 
# st.write("hello world")
# st.header("Header")
# st.subheader("Sub-header")
# st.write("Write")
# st.caption("caption")

st.title("My Demo Page")

name = st.text_input("Enter your name: ")

st.write(f"Hello, {name}")

if st.button("press me"):
    st.write("Hello buddy")

    