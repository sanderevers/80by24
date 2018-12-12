Vue.component('collapsible', {
    props: ['title'],
    data: () => {return { open: false }},
    computed: { clz: function() {return this.open?'item-toggle open':'item-toggle closed';} },
    methods: { toggle: function() {this.open = !this.open;} },
    template: `
        <div class="item">
            <div class="item-header">
                <span v-bind:class="clz" v-on:click="toggle"/>
                {{ title }}&nbsp;
            </div>
            <div v-if="open" class="item-content">
                <slot></slot>
            </div>
        </div>`,
    });
