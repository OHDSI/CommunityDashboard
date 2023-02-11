import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTabsModule } from '@angular/material/tabs';
import { IframePlotComponent } from '../iframe-plot/iframe-plot.component';


@Component({
  selector: 'app-pub-med-tabs',
  standalone: true,
  imports: [
    IframePlotComponent,
    MatTabsModule,
    CommonModule
  ],
  templateUrl: './pub-med-tabs.component.html',
  styleUrls: ['./pub-med-tabs.component.css']
})
export class PubMedTabsComponent {
}
