import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ActivatedRoute } from '@angular/router';
import { OnInit } from '@angular/core';
import { OnDestroy } from '@angular/core';
import { Subscription } from 'rxjs';

@Component({
  selector: 'lib-crumb',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './crumb.component.html',
  styleUrls: ['./crumb.component.css']
})
export class CrumbComponent implements OnInit, OnDestroy {

  crumb: string | null = null

  constructor(
    private router: Router,
    private route: ActivatedRoute,
  ){}
  
  ngOnInit(): void {
    this.subscriptions.push(
      this.route.paramMap.subscribe(
        p => {
          this.crumb = p.get('projectId')
        }
      )
    )
  }

  subscriptions: Subscription[] = []
    
  ngOnDestroy(): void {
    for(const s of this.subscriptions) {
      s.unsubscribe()
    }
  }

  backToProjects() {
    this.router.navigate(['../..'], {relativeTo: this.route})
  }
}
