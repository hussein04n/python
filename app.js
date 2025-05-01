<script>
  let currentQuestion = 0;
  let questions = [];
  let selectedSubjectId = "";
  let selectedLectureId = "";

  const subjectSelect = document.getElementById('subject-select');
  const lectureSelect = document.getElementById('lecture-select');
  const loadQuizBtn = document.getElementById('load-quiz');

  const subjectNameEl = document.getElementById('subject-name');
  const lectureNameEl = document.getElementById('lecture-name');
  const questionText = document.getElementById('question-text');
  const optionsList = document.getElementById('options-list');
  const prevBtn = document.getElementById('prev-btn');
  const nextBtn = document.getElementById('next-btn');
  const questionContainer = document.getElementById('question-container');

  async function loadSubjects() {
    const snapshot = await db.collection("subjects").get();
    snapshot.forEach(doc => {
      const option = document.createElement("option");
      option.value = doc.id;
      option.textContent = doc.data().name;
      subjectSelect.appendChild(option);
    });
  }

  subjectSelect.addEventListener('change', async () => {
    lectureSelect.innerHTML = '<option value="">Select Lecture</option>';
    const subjectId = subjectSelect.value;
    if (!subjectId) return;

    const lecturesSnap = await db.collection("subjects")
      .doc(subjectId)
      .collection("lectures").get();

    lecturesSnap.forEach(doc => {
      const data = doc.data();
      const option = document.createElement("option");
      option.value = doc.id;
      option.textContent = `Lecture ${data.number}: ${data.title}`;
      lectureSelect.appendChild(option);
    });
  });

  loadQuizBtn.addEventListener('click', () => {
    selectedSubjectId = subjectSelect.value;
    selectedLectureId = lectureSelect.value;
    if (selectedSubjectId && selectedLectureId) {
      fetchData();
    }
  });

  async function fetchData() {
    const subjectSnap = await db.collection("subjects").doc(selectedSubjectId).get();
    const lectureSnap = await db.collection("subjects")
      .doc(selectedSubjectId)
      .collection("lectures")
      .doc(selectedLectureId).get();

    const questionsSnap = await db.collection("subjects")
      .doc(selectedSubjectId)
      .collection("lectures")
      .doc(selectedLectureId)
      .collection("questions").get();

    subjectNameEl.textContent = `Subject: ${subjectSnap.data().name}`;
    lectureNameEl.textContent = `Lecture ${lectureSnap.data().number}: ${lectureSnap.data().title}`;

    questions = questionsSnap.docs.map(doc => doc.data());
    currentQuestion = 0;
    displayQuestion();
    questionContainer.style.display = 'block';
  }

  function displayQuestion() {
    if (questions.length === 0) return;

    const q = questions[currentQuestion];
    questionText.textContent = q.question;
    optionsList.innerHTML = "";

    q.options.forEach(option => {
      const li = document.createElement("li");
      li.textContent = option;
      li.onclick = () => selectOption(li);
      optionsList.appendChild(li);
    });
  }

  function selectOption(el) {
    Array.from(optionsList.children).forEach(li => li.style.background = "#f9fafb");
    el.style.background = "#93c5fd";
  }

  nextBtn.addEventListener('click', () => {
    if (currentQuestion < questions.length - 1) {
      currentQuestion++;
      displayQuestion();
    }
  });

  prevBtn.addEventListener('click', () => {
    if (currentQuestion > 0) {
      currentQuestion--;
      displayQuestion();
    }
  });

  loadSubjects();
</script>
