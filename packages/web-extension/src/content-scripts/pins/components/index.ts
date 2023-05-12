import { defineCustomElement } from 'vue'
import ClientPinActivities from './ClientPinActivities.ce.vue'
import '@webcomponents/webcomponentsjs/webcomponents-bundle'

const CustomPinActivities = defineCustomElement(ClientPinActivities)

// 分别导出元素
export { CustomPinActivities }

export function register() {
    customElements.define('gij-pin-activity', CustomPinActivities)
}