import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import {MatCardModule} from '@angular/material/card';

@Component({
  selector: 'app-welcome',
  standalone: true,
  imports: [
    MatCardModule,
    CommonModule
  ],
  templateUrl: './dashboard-welcome.component.html',
  styleUrls: ['./dashboard-welcome.component.css']
})
export class WelcomeComponent {

}
