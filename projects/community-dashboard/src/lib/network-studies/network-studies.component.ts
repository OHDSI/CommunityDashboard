import { Component } from '@angular/core';
import { VisualizationTabsComponent } from "../visualization-tabs/visualization-tabs.component";
import { NetworkStudyListComponent } from "./network-study-list/network-study-list.component";


import { CommonModule } from '@angular/common';

@Component({
    selector: 'lib-network-studies',
    standalone: true,
    templateUrl: './network-studies.component.html',
    styleUrls: [
        './network-studies.component.css'
    ],
    imports: [
        VisualizationTabsComponent,
        NetworkStudyListComponent,
        CommonModule,
    ]
})
export class NetworkStudiesComponent {

}
