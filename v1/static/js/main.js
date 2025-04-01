// Funkcja do renderowania wykresu Chart.js
function renderChart(container, chartData) {
    // Stwórz nowy canvas dla wykresu
    const canvas = document.createElement('canvas');
    container.appendChild(canvas);
    
    // Utwórz wykres Chart.js
    new Chart(canvas, {
        type: 'line',
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: chartData.datasets.length > 1,
                    position: 'top',
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                }
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: false
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    display: true,
                    title: {
                        display: false
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                }
            }
        }
    });
}

// Funkcja do ładowania wykresu bota
function loadBotChart(botId, container) {
    const chartContainer = document.getElementById(container);
    if (!chartContainer) return;

    // Pokaż indykator ładowania
    chartContainer.innerHTML = '<div class="text-center p-5"><div class="spinner-border text-primary" role="status"></div><p class="mt-2">Generowanie wykresu...</p></div>';

    // Pobierz wykres z API
    fetch(`/v1/ai/bot/${botId}/chart`)
        .then(response => response.json())
        .then(data => {
            // Wyczyść container
            chartContainer.innerHTML = '';

            if (data.status === 'success') {
                // Sprawdź typ wykresu (obraz lub chartjs)
                if (data.chart_type === 'image' && data.chart_image) {
                    // Stwórz element img dla obrazu
                    const img = document.createElement('img');
                    img.src = data.chart_image;
                    img.className = 'img-fluid mx-auto d-block';
                    img.alt = 'Wykres zysków bota';
                    chartContainer.appendChild(img);
                } 
                else if (data.chart_type === 'chartjs' && data.chart_data) {
                    // Renderuj wykres Chart.js
                    renderChart(chartContainer, JSON.parse(data.chart_data));
                } 
                else {
                    chartContainer.innerHTML = '<div class="alert alert-warning">Nie udało się wygenerować wykresu.</div>';
                }

                // Aktualizuj analizę bota jeśli istnieje
                if (data.bot_info) {
                    const botInfoContainer = document.getElementById('bot-info');
                    if (botInfoContainer) {
                        botInfoContainer.innerHTML = data.bot_info;
                    }
                }

                // Aktualizuj szczegółową analizę jeśli istnieje
                if (data.detailed_analysis) {
                    const detailedAnalysisContainer = document.getElementById('detailed-analysis');
                    if (detailedAnalysisContainer) {
                        detailedAnalysisContainer.innerHTML = data.detailed_analysis;
                    }
                }
            } else {
                // Obsługa błędu
                chartContainer.innerHTML = `<div class="alert alert-danger">${data.message || 'Nie udało się wygenerować wykresu.'}</div>`;
            }
        })
        .catch(error => {
            console.error('Błąd podczas pobierania wykresu:', error);
            chartContainer.innerHTML = `<div class="alert alert-danger">Wystąpił błąd podczas generowania wykresu.</div>`;
        });
}

// Funkcja do ładowania wykresu portfolio
function loadPortfolioChart(container, strategy = null, period = null) {
    const chartContainer = document.getElementById(container);
    if (!chartContainer) return;

    // Pokaż indykator ładowania
    chartContainer.innerHTML = '<div class="text-center p-5"><div class="spinner-border text-primary" role="status"></div><p class="mt-2">Generowanie wykresu portfela...</p></div>';

    // Budowanie URL z parametrami
    let url = '/v1/ai/portfolio/chart';
    const params = [];
    if (strategy) params.push(`strategy=${encodeURIComponent(strategy)}`);
    if (period) params.push(`period=${encodeURIComponent(period)}`);
    if (params.length > 0) url += '?' + params.join('&');

    // Pobierz wykres z API
    fetch(url)
        .then(response => response.json())
        .then(data => {
            // Wyczyść container
            chartContainer.innerHTML = '';

            if (data.status === 'success') {
                // Sprawdź typ wykresu (obraz lub chartjs)
                if (data.chart_type === 'image' && data.chart_image) {
                    // Stwórz element img dla obrazu
                    const img = document.createElement('img');
                    img.src = data.chart_image;
                    img.className = 'img-fluid mx-auto d-block';
                    img.alt = 'Wykres portfela';
                    chartContainer.appendChild(img);
                } 
                else if (data.chart_type === 'chartjs' && data.chart_data) {
                    // Renderuj wykres Chart.js
                    renderChart(chartContainer, JSON.parse(data.chart_data));
                } 
                else {
                    chartContainer.innerHTML = '<div class="alert alert-warning">Nie udało się wygenerować wykresu.</div>';
                }

                // Aktualizuj analizę portfela jeśli istnieje
                if (data.portfolio_analysis) {
                    const portfolioAnalysisContainer = document.getElementById('portfolio-analysis');
                    if (portfolioAnalysisContainer) {
                        portfolioAnalysisContainer.innerHTML = data.portfolio_analysis;
                    }
                }
            } else {
                // Obsługa błędu
                chartContainer.innerHTML = `<div class="alert alert-danger">${data.message || 'Nie udało się wygenerować wykresu portfela.'}</div>`;
            }
        })
        .catch(error => {
            console.error('Błąd podczas pobierania wykresu portfela:', error);
            chartContainer.innerHTML = `<div class="alert alert-danger">Wystąpił błąd podczas generowania wykresu portfela.</div>`;
        });
}

// Inicjalizacja wykresów po załadowaniu strony
document.addEventListener('DOMContentLoaded', function() {
    // Inicjalizacja wykresu bota jeśli istnieje kontener
    const botChartContainer = document.getElementById('bot-chart-container');
    if (botChartContainer) {
        const botId = botChartContainer.dataset.botId;
        if (botId) {
            loadBotChart(botId, botChartContainer);
        }
    }
    
    // Inicjalizacja wykresu portfolio jeśli istnieje kontener
    const portfolioChartContainer = document.getElementById('portfolio-chart-container');
    if (portfolioChartContainer) {
        loadPortfolioChart(portfolioChartContainer);
    }
    
    // Obsługa filtrów strategii
    const strategyFilter = document.getElementById('strategy-filter');
    if (strategyFilter) {
        strategyFilter.addEventListener('change', function() {
            if (portfolioChartContainer) {
                loadPortfolioChart(portfolioChartContainer, this.value);
            }
        });
    }
    
    // Obsługa filtru okresu
    const periodFilter = document.getElementById('period-filter');
    if (periodFilter) {
        periodFilter.addEventListener('change', function() {
            if (portfolioChartContainer) {
                const strategy = strategyFilter ? strategyFilter.value : null;
                loadPortfolioChart(portfolioChartContainer, strategy, this.value);
            }
        });
    }
}); 