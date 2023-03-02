import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTabsModule } from '@angular/material/tabs';
import { IframePlotComponent } from '../iframe-plot/iframe-plot.component';


@Component({
  selector: 'app-ehden-tabs',
  standalone: true,
  imports: [
    IframePlotComponent,
    MatTabsModule,
    CommonModule
  ],
  templateUrl: './ehden-tabs.component.html',
  styleUrls: ['./ehden-tabs.component.css']
})
export class EhdenTabsComponent {
}
