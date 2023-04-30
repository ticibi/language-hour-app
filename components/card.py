import streamlit as st

def card(title, text):
    # Style the card
    st.markdown(
        """
        <style>
        .card {
            padding: 1rem;
            margin-bottom: 5px;
            background-color: rgb(14, 17, 23);
            box-shadow: 0 3px 4px rgba(0, 0, 0, 1);
            border-radius: 0.25rem;
            border: 1px solid rgba(0, 0, 0, 0.125);
        }
        .card-title {
            color: #4B71FF;
        }
        .card-text {
            color:whitesmoke;
        }
        .card:hover {
            background-color: rgb(25, 30, 35);
            cursor: pointer;
        }
        .card-header {
            font-size: 1.25rem;
            margin-bottom: 0.5rem;
        }
        .card-body {
            font-size: 1rem;
            line-height: 1;
            margin-bottom: 0.5rem;
        }
        </style>
        """
        ,
        unsafe_allow_html=True
    )

    jquery_code = """
        <script>
            $(document).ready(function() {
                $('.message').click(function() {
                    var message_id = $(this).data('id');
                    $.ajax({
                        type: 'POST',
                        url: '/mark_as_read',
                        data: {message_id: message_id},
                        success: function() {
                            $(this).addClass('read');
                        }
                    });
                });
            });
        </script>
    """

    # Html the card
    st.markdown(
        f"""
        <div onclick="mark_as_read()" class="card">
            <div class="card-body card-title">{title}
            <div class="card-body card-text">{text}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


