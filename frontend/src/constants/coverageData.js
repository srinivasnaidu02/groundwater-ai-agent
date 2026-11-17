export const DATASET_COVERAGE_2022 = {
  "Andhra Pradesh": ["Guntur", "Tirupati (Chittoor)", "Vijayawada (Krishna)", "Visakhapatnam"],
  "Arunachal Pradesh": ["Itanagar (Papum Pare)"],
  "Assam": ["Dibrugarh", "Guwahati (Kamrup)"],
  "Bihar": [
    "Araria", "Arwal", "Aurangabad", "Banka", "Begusarai", "Bettiah (West Champaran)",
    "Bhagalpur", "Bhojpur", "Buxar", "Darbhanga", "Gaya", "Gopalganj", "Jamui",
    "Jehanabad", "Kaimur", "Katihar", "Khagaria", "Kishanganj", "Lakhisarai",
    "Madhepura", "Madhubani", "Motihari (East Champaran)", "Munger", "Muzaffarpur",
    "Nalanda", "Nawada", "Patna", "Purnia", "Rohtas", "Saharsa", "Samastipur",
    "Saran", "Sheikhpura", "Sheohar", "Sitamarhi", "Siwan", "Supaul", "Vaishali"
  ],
  "Chhattisgarh": ["Bilaspur", "Raipur"],
  "Delhi": ["East Delhi", "North Delhi", "South Delhi", "West Delhi"],
  "Goa": ["North Goa", "South Goa"],
  "Gujarat": ["Ahmedabad", "Gandhinagar", "Kutch", "Rajkot", "Surat", "Vadodara"],
  "Haryana": ["Faridabad", "Gurugram", "Karnal", "Panipat", "Rohtak"],
  "Himachal Pradesh": ["Kangra", "Shimla"],
  "Jammu and Kashmir": ["Jammu", "Srinagar"],
  "Jharkhand": ["Dhanbad", "Jamshedpur (East Singhbhum)", "Ranchi"],
  "Karnataka": ["Bangalore (Urban)", "Belgaum", "Gulbarga", "Hubli-Dharwad", "Mysore"],
  "Kerala": ["Kochi (Ernakulam)", "Thiruvananthapuram"],
  "Ladakh": ["Leh"],
  "Madhya Pradesh": ["Bhopal", "Gwalior", "Indore", "Jabalpur", "Rewa", "Sagar", "Ujjain"],
  "Maharashtra": ["Aurangabad", "Latur", "Mumbai", "Nagpur", "Nashik", "Pune", "Solapur"],
  "Manipur": ["Imphal West"],
  "Meghalaya": ["East Khasi Hills (Shillong)"],
  "Mizoram": ["Aizawl"],
  "Nagaland": ["Kohima"],
  "Odisha": ["Bhubaneswar (Khurda)", "Cuttack"],
  "Punjab": ["Amritsar", "Bathinda", "Jalandhar", "Ludhiana", "Patiala"],
  "Rajasthan": ["Ajmer", "Alwar", "Bharatpur", "Bikaner", "Jaipur", "Jodhpur", "Kota", "Udaipur"],
  "Sikkim": ["East Sikkim (Gangtok)"],
  "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Salem", "Tirunelveli"],
  "Telangana": ["Hyderabad", "Khammam", "Warangal"],
  "Tripura": ["West Tripura (Agartala)"],
  "Uttar Pradesh": [
    "Agra", "Aligarh", "Allahabad (Prayagraj)", "Bareilly", "Deoria", "Gorakhpur",
    "Jhansi", "Kanpur", "Lucknow", "Mathura", "Mau", "Meerut", "Muzaffarnagar", "Varanasi"
  ],
  "Uttarakhand": ["Dehradun", "Haridwar"],
  "West Bengal": ["Asansol", "Howrah", "Kolkata", "Murshidabad"]
};

export const DATASET_COVERAGE_BENCHMARK = {
  "Bihar": ["Aurangabad", "Bhagalpur", "Darbhanga", "Gaya", "Muzaffarpur", "Nalanda", "Nawada", "Patna", "Saran", "Vaishali"],
  "Delhi": ["South Delhi"],
  "Gujarat": ["Ahmedabad", "Surat"],
  "Haryana": ["Faridabad", "Gurugram", "Hisar", "Karnal", "Rohtak"],
  "Karnataka": ["Bangalore (Urban)", "Mysore"],
  "Maharashtra": ["Mumbai", "Nagpur", "Nashik", "Pune"],
  "Punjab": ["Amritsar", "Bathinda", "Jalandhar", "Ludhiana", "Patiala"],
  "Rajasthan": ["Bikaner", "Jaipur", "Jodhpur", "Kota", "Udaipur"],
  "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai"],
  "Uttar Pradesh": ["Allahabad (Prayagraj)", "Kanpur", "Lucknow", "Varanasi"],
  "West Bengal": ["Kolkata"]
};

export const YEAR_TO_COVERAGE_MAP = {
  "2020": DATASET_COVERAGE_BENCHMARK,
  "2022": DATASET_COVERAGE_2022,
  "2023": DATASET_COVERAGE_BENCHMARK,
  "2024": DATASET_COVERAGE_BENCHMARK,
  "2025": DATASET_COVERAGE_BENCHMARK,
  "2026": DATASET_COVERAGE_BENCHMARK,
};

export const SUPPORTED_ASSESSMENT_YEARS = ["2020", "2022", "2023", "2024", "2025", "2026"];
