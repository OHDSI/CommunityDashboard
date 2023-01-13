import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTabsModule } from '@angular/material/tabs';
import { IframePlotComponent } from '../iframe-plot/iframe-plot.component';


@Component({
  selector: 'app-you-tube-tabs',
  standalone: true,
  imports: [
    IframePlotComponent,
    MatTabsModule,
    CommonModule
  ],
  templateUrl: './you-tube-tabs.component.html',
  styleUrls: ['./you-tube-tabs.component.css']
})
export class YouTubeTabsComponent {
}
