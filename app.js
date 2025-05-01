let currentQuestion = 0;
let questions = [];

document.addEventListener('DOMContentLoaded', () => {
  const subjectNameEl = document.getElementById('subject-name');
  const lectureNameEl = document.getElementById('lecture-name');
  const questionText = document.getElementById('question-text');
  const optionsList = document.getElementById('options-list');
  const prevBtn = document.getElementById('prev-btn');
  const nextBtn = document.getElementById('next-btn');

  async function fetchData() {
    const subjectSnap = await db.collection("subjects").doc("subject1").get();
    const lectureSnap = await db.collection("subjects")
      .doc("subject1")
      .collection("lectures")
      .doc("lecture1").get();

    const questionsSnap = await db.collection("subjects")
      .doc("subject1")
      .collection("lectures")
      .doc("lecture1")
      .collection("questions").get();

    subjectNameEl.textContent = `Subject: ${subjectSnap.data().name}`;
    lectureNameEl.textContent = `Lecture ${lectureSnap.data().number}: ${lectureSnap.data().title}`;

    questions = questionsSnap.docs.map(doc => doc.data());
    displayQuestion();
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

  fetchData();
});
