import streamlit as st


def render_checkbox_grid(selected):
    selected_ids = selected["LOCA_ID"].tolist()
    checked_ids = []
    rows = (len(selected_ids) // 6) + 1
    for i in range(rows):
        cols = st.columns(6)
        for j in range(6):
            idx = i * 6 + j
            if idx >= len(selected_ids):
                break
            with cols[j]:
                bh = selected_ids[idx]
                checked = st.checkbox(bh, value=True, key=f"bh_{bh}")
                checked_ids.append((bh, checked))
    return [bh for bh, checked in checked_ids if checked]
