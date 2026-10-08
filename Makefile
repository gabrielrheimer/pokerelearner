run:
	streamlit run app.py

snapshot:
	python parse_learnsets.py
	python parse_moves.py
	python parse_abilities.py
