import streamlit as st
from helper import add_question, add_template
from helper import template_collection, question_collection

st.set_page_config(page_title="CRD Knowledge Bank", layout="wide")
st.title("🧠 CRD Knowledge Bank Admin")

# =========================
# MODE SELECT
# =========================

mode = st.sidebar.radio("Select Mode", ["Questions", "Templates"])

st.sidebar.divider()

# =========================
# DOMAIN + SEGMENT INPUT
# =========================

st.sidebar.subheader("📁 Scope")

domain = st.sidebar.text_input("Domain", placeholder="ex: sp, enterprise, mobility")
segment = st.sidebar.text_input("Segment", placeholder="ex: routing, security, transport")

if not domain or not segment:
    st.warning("⚠️ Enter domain and segment to continue")
    st.stop()

domain = domain.lower().strip()
segment = segment.lower().strip()

# =========================
# COLLECTION SELECT
# =========================

collection = question_collection if mode == "Questions" else template_collection
data = collection.get()

docs = data.get("documents", [])
meta = data.get("metadatas", [])
ids = data.get("ids", [])

# =========================
# FILTER DATA
# =========================

filtered = []

for doc, m, idv in zip(docs, meta, ids):

    if m.get("domain") != domain:
        continue
    if m.get("segment") != segment:
        continue

    filtered.append((doc, m, idv))

st.subheader(f"📦 {mode} in bank → {len(filtered)}")

# =========================
# DISPLAY RECORDS
# =========================

for doc, m, idv in filtered:

    with st.container():

        st.markdown(f"### 🏷 Topic: `{m.get('topic')}`")

        if mode == "Questions":
            st.caption(f"Source: {m.get('source')}")

        st.write(doc)

        col1, col2 = st.columns([1,5])

        with col1:
            if st.button(f"🗑 Delete", key=idv):
                collection.delete(ids=[idv])
                st.success("Deleted")
                st.rerun()

        st.divider()

# =========================
# ADD NEW ENTRY
# =========================

st.subheader("➕ Add New Entry")

topic = st.text_input("Topic (ex: bgp, architecture)")
text = st.text_area("Enter question/template")

if mode == "Questions":
    source = st.selectbox("Source", ["expert", "sme", "generated"])
else:
    source = "template"

if st.button("Save Entry"):

    if not topic or not text:
        st.error("Topic & text required")
        st.stop()

    topic = topic.lower().strip()

    if mode == "Templates":
        add_template(topic, text, domain, segment)
        st.success("✅ Template added")

    else:
        res = add_question(topic, text, source, domain, segment)

        if res["status"] == "duplicate":
            st.warning("⚠️ Similar question exists")
            st.write(res["match"]["similar_question"])
        else:
            st.success("✅ Question added")

st.divider()

# =========================
# BULK UPLOAD (SME JSON)
# =========================

st.subheader("📥 Bulk Upload SME Approved JSON")

uploaded = st.file_uploader("Upload SME approved JSON", type=["json"])

if uploaded:
    import json
    from helper import push_sme_questions_to_bank

    data = json.load(uploaded)
    result = push_sme_questions_to_bank(data)

    st.success(result)
