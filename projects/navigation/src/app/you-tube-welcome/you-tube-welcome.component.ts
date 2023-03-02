import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';

@Component({
  selector: 'app-you-tube-welcome',
  standalone: true,
  imports: [
    MatCardModule,
    CommonModule
  ],
  templateUrl: './you-tube-welcome.component.html',
  styleUrls: ['./you-tube-welcome.component.css']
})
export class YouTubeWelcomeComponent {

}
