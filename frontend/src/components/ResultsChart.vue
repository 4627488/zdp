<template>
    <Line :data="chartData" :options="chartOptions" />
</template>

<script setup lang="ts">
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend
} from 'chart.js'
import { Line } from 'vue-chartjs'
import { computed } from 'vue'

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend
)

const props = defineProps<{
    trainTime: number[]
    testTimeActual: number[]
    results: any[]
}>()

const chartData = computed(() => {
    const trainLength = props.trainTime.length
    const testLength = props.testTimeActual.length
    const totalLength = trainLength + testLength

    const labels = Array.from({ length: totalLength }, (_, i) => i + 1)

    const datasets = [
        {
            label: 'Training Data',
            backgroundColor: '#9E9E9E',
            borderColor: '#9E9E9E',
            data: [...props.trainTime, ...Array(testLength).fill(null)],
            pointRadius: 3,
            borderDash: [5, 5]
        },
        {
            label: 'Actual Test Data',
            backgroundColor: '#000000',
            borderColor: '#000000',
            data: [...Array(trainLength).fill(null), ...props.testTimeActual],
            pointRadius: 4,
            borderWidth: 2
        }
    ]

    const colors = ['#2196F3', '#4CAF50', '#F44336', '#FF9800', '#9C27B0']

    props.results.forEach((res, index) => {
        datasets.push({
            label: res.name,
            backgroundColor: colors[index % colors.length],
            borderColor: colors[index % colors.length],
            data: [...Array(trainLength).fill(null), ...res.predicted_cumulative_time],
            pointRadius: 3,
            borderDash: [2, 2]
        })
    })

    return {
        labels,
        datasets
    }
})

const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        title: {
            display: true,
            text: 'Reliability Prediction Analysis'
        }
    },
    scales: {
        x: {
            title: {
                display: true,
                text: 'Failure Number'
            }
        },
        y: {
            title: {
                display: true,
                text: 'Cumulative Time'
            }
        }
    }
}
</script>
