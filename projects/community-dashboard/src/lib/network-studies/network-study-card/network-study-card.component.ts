import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Input } from '@angular/core';
import { NetworkStudyRepo } from '../../network-study-repo.service';
import { MatCardModule } from '@angular/material/card'; 


@Component({
  selector: 'lib-network-study-card',
  standalone: true,
  imports: [
    MatCardModule,
    CommonModule
  ],
  templateUrl: './network-study-card.component.html',
  styleUrls: ['./network-study-card.component.css']
})
export class NetworkStudyCardComponent {

  @Input({required: true}) networkStudyRepo!: NetworkStudyRepo

  elevateClass = false

  elevate() {
    this.elevateClass = true
  }

  noelevate() {
    this.elevateClass = false
  }
}
