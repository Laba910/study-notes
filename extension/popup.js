document.getElementById("save").addEventListener("click", () => {
  const status = document.getElementById("status");
  status.textContent = "저장 중...";

  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    chrome.tabs.sendMessage(tabs[0].id, { action: "save" }, (response) => {
      if (!response) {
        status.textContent = "오류: 페이지를 새로고침 후 시도하세요";
        return;
      }
      if (response.status === "ok") {
        status.textContent = `저장 완료: ${response.file}`;
      } else if (response.status === "empty") {
        status.textContent = "대화 내용이 없습니다";
      } else {
        status.textContent = `오류: ${response.error || "알 수 없는 오류"}`;
      }
    });
  });
});
