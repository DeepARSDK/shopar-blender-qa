rm -rf __pycache__
cd ..
zip -r shopar_qa.zip shopar_qa -i "*.py" "README.md"
mv shopar_qa.zip shopar_qa/build