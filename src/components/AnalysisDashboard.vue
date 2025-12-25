<template>
    <v-container fluid>
        <!-- Key Metrics Cards -->
        <v-row>
            <v-col cols="12" md="3">
                <v-card :color="analysis.trend_color" variant="tonal">
                    <v-card-item>
                        <v-card-title class="text-h6">{{ $t('analysis.cards.trend.title') }}</v-card-title>
                        <v-card-subtitle>{{ $t('analysis.cards.trend.subtitle', {
                            n: analysis.laplace_factor.toFixed(3)
                        }) }}</v-card-subtitle>
                    </v-card-item>
                    <v-card-text class="text-h5 font-weight-bold">
                        {{ analysis.trend_assessment }}
                    </v-card-text>
                </v-card>
            </v-col>
            <v-col cols="12" md="3">
                <v-card color="primary" variant="tonal">
                    <v-card-item>
                        <v-card-title class="text-h6">{{ $t('analysis.cards.bestModel.title') }}</v-card-title>
                        <v-card-subtitle>{{ $t('analysis.cards.bestModel.subtitle') }}</v-card-subtitle>
                    </v-card-item>
                    <v-card-text class="text-h5 font-weight-bold">
                        {{ analysis.best_model }}
                    </v-card-text>
                </v-card>
            </v-col>
            <v-col cols="12" md="3">
                <v-card color="info" variant="tonal">
                    <v-card-item>
                        <v-card-title class="text-h6">{{ $t('analysis.cards.failures.title') }}</v-card-title>
                        <v-card-subtitle>{{ $t('analysis.cards.failures.subtitle') }}</v-card-subtitle>
                    </v-card-item>
                    <v-card-text class="text-h5 font-weight-bold">
                        {{ analysis.total_failures }}
                    </v-card-text>
                </v-card>
            </v-col>
            <v-col cols="12" md="3">
                <v-card color="secondary" variant="tonal">
                    <v-card-item>
                        <v-card-title class="text-h6">{{ $t('analysis.cards.time.title') }}</v-card-title>
                        <v-card-subtitle>{{ $t('analysis.cards.time.subtitle') }}</v-card-subtitle>
                    </v-card-item>
                    <v-card-text class="text-h5 font-weight-bold">
                        {{ analysis.total_time.toFixed(2) }}
                    </v-card-text>
                </v-card>
            </v-col>
        </v-row>

        <!-- Charts Row 1 -->
        <v-row class="mt-4">
            <v-col cols="12" md="6">
                <v-card>
                    <v-card-title>{{ $t('analysis.charts.intensity.title') }}</v-card-title>
                    <v-card-subtitle>{{ $t('analysis.charts.intensity.subtitle') }}</v-card-subtitle>
                    <v-card-text style="height: 300px;">
                        <Line :data="intensityChartData" :options="commonOptions" />
                    </v-card-text>
                </v-card>
            </v-col>
            <v-col cols="12" md="6">
                <v-card>
                    <v-card-title>{{ $t('analysis.charts.tbf.title') }}</v-card-title>
                    <v-card-subtitle>{{ $t('analysis.charts.tbf.subtitle') }}</v-card-subtitle>
                    <v-card-text style="height: 300px;">
                        <Bar :data="tbfChartData" :options="commonOptions" />
                    </v-card-text>
                </v-card>
            </v-col>
        </v-row>

        <!-- Advanced Charts Row -->
        <v-row class="mt-4" v-if="analysis.rocof">
            <v-col cols="12" md="6">
                <v-card>
                    <v-card-title>{{ $t('analysis.charts.rocof.title') }}</v-card-title>
                    <v-card-text style="height: 300px;">
                        <Line :data="rocofChartData" :options="commonOptions" />
                    </v-card-text>
                </v-card>
            </v-col>
            <v-col cols="12" md="6">
                <v-card>
                    <v-card-title>{{ $t('analysis.charts.cumulative.title') }}</v-card-title>
                    <v-card-text style="height: 300px;">
                        <Line :data="cumulativeChartData" :options="commonOptions" />
                    </v-card-text>
                </v-card>
            </v-col>
        </v-row>

        <v-row class="mt-4" v-if="analysis.reliability_curve">
            <v-col cols="12" md="6">
                <v-card>
                    <v-card-title>{{ $t('analysis.charts.reliability.title') }}</v-card-title>
                    <v-card-text style="height: 300px;">
                        <Line :data="reliabilityChartData" :options="commonOptions" />
                    </v-card-text>
                </v-card>
            </v-col>
            <v-col cols="12" md="6">
                <v-card>
                    <v-card-title>{{ $t('analysis.charts.distribution.title') }}</v-card-title>
                    <v-card-text style="height: 300px;">
                        <Bar :data="distributionChartData" :options="commonOptions" />
                    </v-card-text>
                </v-card>
            </v-col>
        </v-row>

        <!-- DeepSeek Report Section -->
        <v-row class="mt-4" v-if="analysis.deepseek_report">
            <v-col cols="12">
                <v-card color="surface-variant" variant="outlined">
                    <v-card-title class="text-h5">
                        <v-icon icon="mdi-robot" class="mr-2"></v-icon>
                        {{ $t('analysis.deepseek.title') }}
                    </v-card-title>
                    <v-card-text>
                        <div class="text-body-1 markdown-content" v-html="renderedReport"></div>
                    </v-card-text>
                </v-card>
            </v-col>
        </v-row>

        <!-- Insights Section -->
        <v-row class="mt-4">
            <v-col cols="12">
                <v-card>
                    <v-card-title>{{ $t('analysis.insights.title') }}</v-card-title>
                    <v-card-text>
                        <v-list lines="two">
                            <v-list-item prepend-icon="mdi-information">
                                <v-list-item-title>{{ $t('analysis.insights.trend.title') }}</v-list-item-title>
                                <v-list-item-subtitle>
                                    {{ $t('analysis.insights.trend.desc', {
                                        score: analysis.laplace_factor.toFixed(3),
                                        status: analysis.trend_assessment
                                    }) }}
                                </v-list-item-subtitle>
                            </v-list-item>
                            <v-list-item prepend-icon="mdi-trophy">
                                <v-list-item-title>{{ $t('analysis.insights.performance.title') }}</v-list-item-title>
                                <v-list-item-subtitle>
                                    {{ $t('analysis.insights.performance.desc', {
                                        model: analysis.best_model, rmse:
                                            analysis.best_rmse?.toFixed(4)
                                    }) }}
                                </v-list-item-subtitle>
                            </v-list-item>
                        </v-list>
                    </v-card-text>
                </v-card>
            </v-col>
        </v-row>
    </v-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    BarElement,
    Title,
    Tooltip,
    Legend,
    Filler
} from 'chart.js'
import { Line, Bar } from 'vue-chartjs'
import MarkdownIt from 'markdown-it'

const { t } = useI18n()

const md = new MarkdownIt({
    html: true,
    linkify: true,
    typographer: true
})

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    BarElement,
    Title,
    Tooltip,
    Legend,
    Filler
)

const props = defineProps<{
    analysis: any
}>()

const renderedReport = computed(() => {
    if (!props.analysis.deepseek_report) return ''
    return md.render(props.analysis.deepseek_report)
})

const labels = computed(() => Array.from({ length: props.analysis.total_failures }, (_, i) => i + 1))

const intensityChartData = computed(() => ({
    labels: labels.value,
    datasets: [
        {
            label: t('analysis.charts.intensity.smoothed'),
            data: props.analysis.failure_intensity.smoothed,
            borderColor: '#FF9800',
            backgroundColor: 'rgba(255, 152, 0, 0.2)',
            fill: true,
            tension: 0.4,
            pointRadius: 0
        },
        {
            label: t('analysis.charts.intensity.raw'),
            data: props.analysis.failure_intensity.raw,
            borderColor: '#E0E0E0',
            borderWidth: 1,
            pointRadius: 1,
            fill: false
        }
    ]
}))

const tbfChartData = computed(() => ({
    labels: labels.value,
    datasets: [
        {
            label: t('analysis.charts.tbf.label'),
            data: props.analysis.tbf_trend,
            backgroundColor: '#2196F3',
            borderRadius: 2
        }
    ]
}))

const rocofChartData = computed(() => ({
    labels: labels.value,
    datasets: [
        {
            label: t('analysis.charts.rocof.label'),
            data: props.analysis.rocof || [],
            borderColor: '#9C27B0',
            backgroundColor: 'rgba(156, 39, 176, 0.2)',
            fill: true,
            tension: 0.4
        }
    ]
}))

const cumulativeChartData = computed(() => ({
    labels: labels.value,
    datasets: [
        {
            label: t('analysis.charts.cumulative.label'),
            data: props.analysis.cumulative_failures || [],
            borderColor: '#F44336',
            backgroundColor: 'rgba(244, 67, 54, 0.1)',
            fill: true,
            tension: 0.2
        }
    ]
}))

const reliabilityChartData = computed(() => {
    if (!props.analysis.reliability_curve) return { labels: [], datasets: [] }
    return {
        labels: props.analysis.reliability_curve.time_points.map((t: number) => t.toFixed(1)),
        datasets: [
            {
                label: t('analysis.charts.reliability.label'),
                data: props.analysis.reliability_curve.probability,
                borderColor: '#4CAF50',
                backgroundColor: 'rgba(76, 175, 80, 0.2)',
                fill: true,
                tension: 0.1
            }
        ]
    }
})

const distributionChartData = computed(() => {
    if (!props.analysis.failure_distribution) return { labels: [], datasets: [] }
    // bins has n+1 edges, counts has n items. Use edges as labels (ranges)
    const bins = props.analysis.failure_distribution.bins
    const binLabels = []
    for (let i = 0; i < bins.length - 1; i++) {
        binLabels.push(`${bins[i].toFixed(1)} - ${bins[i + 1].toFixed(1)}`)
    }

    return {
        labels: binLabels,
        datasets: [
            {
                label: t('analysis.charts.distribution.label'),
                data: props.analysis.failure_distribution.counts,
                backgroundColor: '#607D8B',
                borderRadius: 4
            }
        ]
    }
})

const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            position: 'top' as const
        }
    },
    scales: {
        x: {
            grid: {
                display: false
            }
        }
    }
}
</script>

<style scoped>
.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3) {
    margin-top: 16px;
    margin-bottom: 8px;
    font-weight: bold;
}

.markdown-content :deep(p) {
    margin-bottom: 12px;
    line-height: 1.6;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
    margin-bottom: 12px;
    padding-left: 24px;
}

.markdown-content :deep(li) {
    margin-bottom: 4px;
}

.markdown-content :deep(code) {
    background-color: rgba(0, 0, 0, 0.05);
    padding: 2px 4px;
    border-radius: 4px;
    font-family: monospace;
}

.markdown-content :deep(pre) {
    background-color: #f5f5f5;
    padding: 12px;
    border-radius: 8px;
    overflow-x: auto;
    margin-bottom: 12px;
}

.markdown-content :deep(pre code) {
    background-color: transparent;
    padding: 0;
}

.markdown-content :deep(blockquote) {
    border-left: 4px solid #e0e0e0;
    padding-left: 16px;
    margin-left: 0;
    color: #757575;
}
</style>
