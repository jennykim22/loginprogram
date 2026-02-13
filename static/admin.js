/* 1. 사이드바 & 유효성 검사 (전역 함수) */
function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    
    if (sidebar && mainContent) {
        sidebar.classList.toggle('closed');
        mainContent.classList.toggle('expanded');
    }
}

let isIdChecked = false;

function validateForm() {
    if (!isIdChecked) {
        alert("아이디 중복을 확인해주세요.");
        return false;
    }
    return true;
}

async function id_overlap_check() {
    const usernameInput = document.getElementById('username');
    const msgElement = document.getElementById('username-msg');

    if (!usernameInput || !msgElement) return; // 요소가 없으면 중단

    const username = usernameInput.value;

    if (!username) {
        msgElement.innerText = "아이디를 입력해주세요.";
        msgElement.style.color = "orange";
        return;
    }

    try {
        const response = await fetch(`/check-username?username=${username}`);
        const data = await response.json();
        
        if (data.available === true || String(data.available) === 'true') {
            msgElement.innerText = "사용 가능한 아이디입니다.";
            msgElement.style.color = "green";
            isIdChecked = true;
        } else {
            msgElement.innerText = "이미 존재하는 아이디입니다.";
            msgElement.style.color = "red";
            isIdChecked = false;
        }
    } catch (error) {
        console.error("아이디 체크 중 에러:", error);
    }
}       

/* 2. 썸머노트 (JQuery) */
$(document).ready(function() {
    const $publishBtn = $('#publishBtn');
    
    // 버튼이 없는 페이지일 수도 있으므로 체크
    if ($publishBtn.length) {
        $publishBtn.prop('disabled', true);
        $publishBtn.css('opacity', '0.5');
        $publishBtn.css('cursor', 'not-allowed');
    }

    // 썸머노트가 있는 경우에만 실행
    if ($('#content').length) {
        $('#content').summernote({
            placeholder: 'Tell your story...',
            tabsize: 2,
            height: 500,               
            lang: 'ko-KR',             
            toolbar: [
                ['style', ['style']],
                ['font', ['bold', 'underline', 'clear']],
                ['color', ['color']],
                ['para', ['ul', 'ol', 'paragraph']],
                ['insert', ['picture', 'link', 'video']],
                ['view', ['fullscreen', 'help']]
            ],
            callbacks: {
                onChange: function(contents, $editable) {
                    checkInputs();
                },
                onImageUpload: function(files) {
                    for (var i = 0; i < files.length; i++) {
                        var reader = new FileReader();
                        reader.onload = function(e) {
                            $('#content').summernote('insertImage', e.target.result);
                        };
                        reader.readAsDataURL(files[i]);
                    }
                }
            }
        });
    }

    $('#title').on('input', function() {
        checkInputs(); 
    });

    function checkInputs() {
        // 요소가 없으면 실행 안 함
        if (!$('#title').length || !$('#content').length || !$publishBtn.length) return;

        var title = $('#title').val().trim();
        var isContentEmpty = $('#content').summernote('isEmpty');

        if (title.length > 0 && !isContentEmpty) {
            $publishBtn.prop('disabled', false); 
            $publishBtn.css('opacity', '1');
            $publishBtn.css('cursor', 'pointer');
        } else {
            $publishBtn.prop('disabled', true);
            $publishBtn.css('opacity', '0.5');
            $publishBtn.css('cursor', 'not-allowed');
        }
    }
});

/* 3. 차트 (Chart.js) */
document.addEventListener('DOMContentLoaded', function() {
    const dataElement = document.getElementById('chart-data');
    if (!dataElement) return; // 차트 데이터 없으면 패스

    try {
        const chartDataObj = JSON.parse(dataElement.textContent);
        const ctx = document.getElementById('postsChart');

        if (ctx) {
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: chartDataObj.labels,
                    datasets: [{
                        label: '작성글 수',
                        data: chartDataObj.values,
                        borderColor: '#1a73e8',
                        backgroundColor: '#1a73e8',
                        fill: false,              
                        tension: 0.3,
                        borderWidth: 2,
                        pointRadius: 4,
                        pointBackgroundColor: '#1a73e8'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true, 
                            labels: {
                                usePointStyle: true, 
                                pointStyle: 'circle'
                            }
                        }
                    },
                    scales: {
                        y: { 
                            beginAtZero: true, 
                            ticks: { stepSize: 1 } 
                        },
                        x: { 
                            ticks: {
                                autoSkip: false,   
                                maxRotation: 0,
                                minRotation: 0
                            },
                            grid: { display: false } 
                        }
                    }
                }
            });
        }
    } catch (e) {
        console.error("차트 로딩 실패:", e);
    }
});
