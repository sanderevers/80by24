Vue.component('collapsible', {
    props: ['title','actions'],
    data: () => {return { open: false }},
    computed: { clz: function() {return this.open?'item-toggle open':'item-toggle closed';} },
    methods: { toggle: function() {this.open = !this.open;} },
    template: `
        <div class="item">
            <div class="item-header" v-on:click="toggle">
                <span :class="clz"/>
                <span>{{ title }} </span>
                <span v-for="action in actions">
                    <a href="#" v-on:click="action.handler">[{{ action.name }}]</a>{{' '}}
                </span>
            </div>
            <div v-if="open" class="item-content">
                <slot></slot>
            </div>
        </div>`,
    });
