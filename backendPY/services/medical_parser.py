import re

def parse_medical_report(text: str):
    """
    Extract structured medical data with hierarchical section awareness.
    Precision V5: Robust Greedy Continuation (fixes medicine row fragmentation).
    """
    print("--- PARSING START (Precision V5) ---")
    data = {
        "patientInfo": {"name": "N/A", "age": "N/A", "gender": "N/A", "date": "N/A"},
        "testResults": [],
        "medicines": [],
        "diagnosis": "",
        "advice": ""
    }

    # Labels and metadata to filter out
    BLACKLIST = {
        "medicine", "medicine name", "medicine id", "instruction", "dosage", "frequency", "duration", 
        "timing", "days", "dose", "patient name", "name", "age", "gender", "sex", "date", "hospital",
        "doctor", "advice", "diagnosis", "clinical findings", "hospital name", "report", "format", 
        "signature", "authorized", "page", "id"
    }

    def is_junk(value: str) -> bool:
        v = value.lower().strip().strip(':')
        return v in BLACKLIST or len(v) < 1

    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if not lines:
        return data

    # 1. Flexible Header Discovery
    SECTION_KEYWORDS = {
        "DIAG": [r"\bdiagnosis\b", r"\bclinical findings\b", r"\bimpression\b", r"\bclinical history\b", r"\bgnosi\b"],
        "MEDS": [r"\bprescribed medicines\b", r"\bmedicine name\b", r"\bmedicine\b\s+(?:dose|dosage|instruction|timing)", r"\bmedicine\b\s*[:\t]", r"^medicine\s*$", r"^rx\b", r"\bmedication list\b"],
        "ADVICE": [r"\badvice\b", r"\bdoctor's advice\b", r"\binstructions\b", r"\bnote\b", r"\bfollow up\b"],
        "LAB": [r"\blab results\b", r"\binvestigation\b", r"\btest report\b", r"\breport summary\b"]
    }
    
    MED_TABLE_HEADERS = ["medicine", "dose", "dosage", "timing", "days", "instruction"]

    all_headers = []
    for i, line in enumerate(lines):
        low = line.lower()
        if i == 0 and ("format" in low or "prescription" in low): continue
            
        header_found = False
        for key, patterns in SECTION_KEYWORDS.items():
            for p in patterns:
                if re.search(p, low):
                    all_headers.append((i, key))
                    header_found = True
                    break
            if header_found: break
        
        if not header_found:
            hits = sum(1 for h in MED_TABLE_HEADERS if h in low)
            if hits >= 2: all_headers.append((i, "MEDS"))

    all_headers.sort()
    unique_headers = []
    seen = set()
    for h in all_headers:
        if h[0] not in seen:
            unique_headers.append(h)
            seen.add(h[0])
    all_headers = unique_headers

    # 2. Extract Patient Info
    patient_block = lines[:40]
    for i, line in enumerate(patient_block):
        low = line.lower()
        if "patient name" in low or re.search(r"^name\s*[:\t]", low):
            val = line.split(":", 1)[1].strip() if ":" in line else ""
            if not val and i + 1 < len(patient_block): val = patient_block[i+1].strip()
            if val and not is_junk(val): data["patientInfo"]["name"] = val.strip(':').strip()

        if "age" in low or "gender" in low or "29" in low: 
             m = re.search(r"(\d+)\s*/\s*(Male|Female|M|F)", line, re.I)
             if m: data["patientInfo"]["age"], data["patientInfo"]["gender"] = m.groups()
             elif i + 1 < len(patient_block):
                 m = re.search(r"(\d+)\s*/\s*(Male|Female|M|F)", patient_block[i+1], re.I)
                 if m: data["patientInfo"]["age"], data["patientInfo"]["gender"] = m.groups()

        if "date" in low:
            val = line.split(":", 1)[1].strip() if ":" in line else ""
            if not val and i+1 < len(patient_block): val = patient_block[i+1].strip()
            if val and len(val) > 5: data["patientInfo"]["date"] = val

    # 3. Process Content Between Headers
    diagnosis_parts = []
    advice_parts = []

    for idx, (start_line, section_key) in enumerate(all_headers):
        end_line = all_headers[idx+1][0] if idx + 1 < len(all_headers) else len(lines)
        section_content = lines[start_line+1 : end_line]
        
        if section_key == "DIAG":
            first_line = lines[start_line]
            if ":" in first_line: diagnosis_parts.append(first_line.split(":", 1)[1].strip())
            diagnosis_parts.append(" ".join(section_content).strip())
            
        elif section_key == "ADVICE":
            first_line = lines[start_line]
            if ":" in first_line: advice_parts.append(first_line.split(":", 1)[1].strip())
            advice_parts.append(" ".join(section_content).strip())
            
        elif section_key == "MEDS":
            med_records = []
            current_med = None
            
            # Keywords to identify columns
            # Strength/Unit markers (should NOT trigger a new medicine name on their own if they follow a name)
            DOSAGE_KEYWORDS = ["tablet", "cap", "ml", "spoon", "puff", "inj", "unit", "tsp"]
            FREQ_KEYWORDS = ["morning", "night", "daily", "once", "twice", "od", "bd", "tid", "qid", "breakfast", "dinner", "after", "before"]
            DURATION_KEYWORDS = ["days", "weeks", "months", "day"]
            
            # Markers that HIGHLY suggest a medicine name
            NAME_MARKERS = ["mg", "mcg", "ml", "gm", "syrup", "suspension", "ointment", "drops"]

            for line in section_content:
                low_l = line.lower()
                if is_junk(line): continue
                if any(k in low_l for k in ["advice:", "doctor:", "signature:"]): break
                
                parts = re.split(r'[:\t|]|\s{2,}', line)
                parts = [p.strip() for p in parts if p.strip()]
                
                # REFINED NEW MEDICINE LOGIC
                is_new_med = False
                potential_name = parts[0]
                
                # Horizontal row (3+ parts) is almost always a new medicine
                if len(parts) >= 3:
                    is_new_med = True
                else:
                    # Check if it's a DOSAGE/FREQ continuation
                    is_continuation = False
                    if current_med:
                        # If the line starts with a number followed by a dosage unit, it's likely dosage
                        if re.match(r'^\d+\s*(' + '|'.join(DOSAGE_KEYWORDS) + r')', low_l):
                            is_continuation = True
                        # If it strictly matches frequency keywords
                        elif any(word in low_l for word in FREQ_KEYWORDS) and len(low_l) < 30:
                            is_continuation = True
                        # If it's a duration (X days)
                        elif re.search(r'\d+\s*(' + '|'.join(DURATION_KEYWORDS) + r')', low_l):
                            is_continuation = True
                    
                    if not is_continuation:
                        # Check if it looks like a name
                        if any(m in low_l for m in NAME_MARKERS):
                            is_new_med = True
                        elif potential_name[0].isupper() and len(potential_name) > 4:
                            is_new_med = True

                if is_new_med:
                    if current_med: med_records.append(current_med)
                    current_med = {"name": potential_name, "dosage": "N/A", "frequency": "N/A", "duration": "N/A"}
                    
                    if len(parts) >= 2:
                         # Assign remaining parts intelligently
                         for p in parts[1:]:
                             low_p = p.lower()
                             if any(k in low_p for k in DOSAGE_KEYWORDS): current_med["dosage"] = p
                             elif any(k in low_p for k in FREQ_KEYWORDS): current_med["frequency"] = p
                             elif any(k in low_p for k in DURATION_KEYWORDS) or re.search(r'^\d+$', p): current_med["duration"] = p
                             else:
                                 # Fallback: assign to first N/A
                                 if current_med["dosage"] == "N/A": current_med["dosage"] = p
                                 elif current_med["frequency"] == "N/A": current_med["frequency"] = p
                elif current_med:
                    # CONTINUATION LOGIC
                    if any(k in low_l for k in DOSAGE_KEYWORDS) and current_med["dosage"] == "N/A":
                        current_med["dosage"] = line
                    elif any(k in low_l for k in FREQ_KEYWORDS) and current_med["frequency"] == "N/A":
                        current_med["frequency"] = line
                    elif (re.search(r'\d+', line) or any(k in low_l for k in DURATION_KEYWORDS)) and current_med["duration"] == "N/A":
                        current_med["duration"] = line
                    else:
                        # Default append
                        if current_med["dosage"] == "N/A": current_med["dosage"] = line
                        elif current_med["frequency"] == "N/A": current_med["frequency"] = line

            if current_med: med_records.append(current_med)
            data["medicines"].extend(med_records)

        elif section_key == "LAB":
            for line in section_content:
                row = [p.strip() for p in re.split(r'[:\t|]|\s{2,}', line) if p.strip()]
                if len(row) >= 2 and not is_junk(row[0]):
                    data["testResults"].append({
                        "parameter": row[0], "result": row[1],
                        "unit": row[2] if len(row) > 2 else "",
                        "range": row[3] if len(row) > 3 else "N/A"
                    })

    # 4. Cleanup
    data["diagnosis"] = " ".join([p for p in diagnosis_parts if p]).strip()
    data["advice"] = " ".join([p for p in advice_parts if p]).strip()
    
    # Deduplicate and final check
    seen = set()
    final_meds = []
    for m in data["medicines"]:
        name_key = m['name'].lower()
        if name_key not in seen and not is_junk(m['name']):
            seen.add(name_key)
            final_meds.append(m)
    data["medicines"] = final_meds

    print(f"--- PARSING COMPLETE: {len(data['medicines'])} medicines identified ---")
    return data
