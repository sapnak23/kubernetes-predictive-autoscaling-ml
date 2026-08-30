import http from 'k6/http';
import { check, sleep } from 'k6';


const TARGET_URL = __ENV.TARGET_URL;


// Workload intensity levels
const LOW = 5;
const MEDIUM = 20;
const HIGH = 50;
const SPIKE = 100;


export const options = {

    stages: [

        // ==================================================
        // PHASE 1 — LOW / GRADUAL RAMP / MEDIUM
        // Total: 100 minutes
        // ==================================================

        // Gradually enter low load
        { duration: '10m', target: LOW },

        // Stable low load
        { duration: '10m', target: LOW },

        // Gradual increase
        { duration: '30m', target: MEDIUM },

        // Stable medium
        { duration: '15m', target: MEDIUM },

        // Sudden rise
        { duration: '5m', target: SPIKE },

        // Hold spike
        { duration: '10m', target: SPIKE },

        // Recovery toward medium
        { duration: '10m', target: MEDIUM },

        // Recovery toward low
        { duration: '10m', target: LOW },


        // ==================================================
        // PHASE 2 — OSCILLATING
        // Total: 40 minutes
        // Running total: 140 min
        // ==================================================

        { duration: '5m', target: HIGH },
        { duration: '5m', target: MEDIUM },
        { duration: '5m', target: HIGH },
        { duration: '5m', target: LOW },

        { duration: '5m', target: HIGH },
        { duration: '5m', target: MEDIUM },
        { duration: '5m', target: HIGH },
        { duration: '5m', target: LOW },


        // ==================================================
        // PHASE 3 — LONG RAMP + HIGH + SUDDEN DROP
        // Total: 70 minutes
        // Running total: 210 min
        // ==================================================

        // Slow increase
        { duration: '30m', target: HIGH },

        // Sustained high workload
        { duration: '20m', target: HIGH },

        // Sudden decrease
        { duration: '5m', target: LOW },

        // Stable recovery
        { duration: '15m', target: LOW },


        // ==================================================
        // PHASE 4 — RANDOM / BURST-LIKE CHANGES
        // Total: 30 minutes
        // Running total: 240 min
        // ==================================================

        { duration: '3m', target: HIGH },
        { duration: '3m', target: LOW },

        { duration: '3m', target: SPIKE },
        { duration: '3m', target: MEDIUM },

        { duration: '3m', target: HIGH },
        { duration: '3m', target: LOW },

        { duration: '3m', target: SPIKE },
        { duration: '3m', target: MEDIUM },

        { duration: '3m', target: HIGH },
        { duration: '3m', target: LOW },


        // ==================================================
        // PHASE 5 — SECOND RAMP + SPIKE
        // Total: 90 minutes
        // Running total: 330 min
        // ==================================================

        // Gradual rise again
        { duration: '30m', target: HIGH },

        // Stable high
        { duration: '15m', target: HIGH },

        // Fast spike
        { duration: '5m', target: SPIKE },

        // Sustained spike
        { duration: '10m', target: SPIKE },

        // Gradual recovery
        { duration: '15m', target: MEDIUM },

        // Back to low
        { duration: '15m', target: LOW },


        // ==================================================
        // PHASE 6 — FINAL OSCILLATION + RECOVERY
        // Total: 30 minutes
        // GRAND TOTAL: 360 min = 6 HOURS
        // ==================================================

        { duration: '5m', target: MEDIUM },
        { duration: '5m', target: HIGH },
        { duration: '5m', target: SPIKE },
        { duration: '5m', target: LOW },

        // Finish smoothly at zero
        { duration: '10m', target: 0 },
    ],

    thresholds: {
        http_req_failed: ['rate<0.20'],
    },

    gracefulRampDown: '30s',
};


export default function () {

    const response = http.get(TARGET_URL);

    check(response, {
        'HTTP response received':
            (r) => r.status >= 200 && r.status < 500,
    });

    sleep(1);
}