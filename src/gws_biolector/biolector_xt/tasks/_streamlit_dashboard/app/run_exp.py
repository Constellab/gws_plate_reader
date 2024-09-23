import streamlit as st


def run_exp_main():

    with st.form(key='run_exp'):

        protocol_file = st.file_uploader("Protofile file", type=['json'])

        metadata_file = st.file_uploader("Metadata file", type=['csv'])

        # if protocol_file and metadata_file:
        #     st.write("Both files uploaded")

        if st.form_submit_button("Run experiment"):

            if not protocol_file:
                st.error("Please upload a protocol file")
                return

            if not metadata_file:
                st.error("Please upload a metadata file")
                return

            st.write("Running experiment")
