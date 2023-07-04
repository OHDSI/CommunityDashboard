import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ProjectSearchComponent } from './project-search/project-search.component';
import { RouterModule } from '@angular/router';
import { ViewChild } from '@angular/core';
import { MatGridListModule } from '@angular/material/grid-list'; 
import { BehaviorSubject, Observable, Subscription, map, of, startWith } from 'rxjs';
import { Project } from '../project.service';
import { ProjectCardComponent } from './project-card/project-card.component';
import { DocsService, Query, SearchService, SearchTableDataSource } from '@commonshcs-angular';
import { AfterViewInit } from '@angular/core';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTable, MatTableModule } from '@angular/material/table';
import { Inject } from '@angular/core';
import { OnDestroy } from '@angular/core';
import { switchMap } from 'rxjs/operators';
import { Router } from '@angular/router';
import { ActivatedRoute } from '@angular/router';


@Component({
  selector: 'lib-project-list',
  standalone: true,
  imports: [
    ProjectSearchComponent,
    ProjectCardComponent,
    MatTableModule,
    MatSortModule,
    MatPaginatorModule,
    MatGridListModule,
    RouterModule,
    CommonModule
  ],
  templateUrl: './project-list.component.html',
  styleUrls: ['./project-list.component.css']
})
export class ProjectListComponent implements AfterViewInit, OnDestroy {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild(MatTable) table!: MatTable<Project>;
  @ViewChild(ProjectSearchComponent) projectSearchComponent?: ProjectSearchComponent;

  featuredProjects: Observable<Project[] | null> = this.docsService.valueChanges({
    path: 'project',
    where: [['featured', '==', true]]
  })
  mostActiveProjects: Observable<Project[] | null> = this.docsService.valueChanges({
    path: 'project',
    where: [['active', '==', true]]
  })
  dataSource!: SearchTableDataSource<Project>
  count = new BehaviorSubject(0)
  displayedColumns: string[] = ['id'];


  constructor(
    @Inject('SearchService') private searchService: SearchService,
    @Inject('DocsService')private docsService: DocsService,
    private router: Router,
    private route: ActivatedRoute,
  ){}

  ngAfterViewInit(): void {
    const searchQuery = this.projectSearchComponent!.searchControl.valueChanges.pipe(
      startWith(''),
      map((q) => {
        return {
          q: {
            value: q,
          }
        } as Query
      })
    )
    setTimeout(() => this.subscriptions.push(
      searchQuery.pipe(
        switchMap(query => this.searchService.count({
          index: 'project',
          query
        }))
      ).subscribe(this.count)
    ))
    this.dataSource = new SearchTableDataSource(
      this.searchService,
      'project',
      searchQuery
    )
    this.dataSource.sort = this.sort;
    this.dataSource.paginator = this.paginator;
    this.table.dataSource = this.dataSource;
  }

  subscriptions: Subscription[] = []

  ngOnDestroy(): void {
    for (const s of this.subscriptions) {
      s.unsubscribe()
    }
  }

  drillDown(row: Project) {
    this.router.navigate(['project', row.id], {relativeTo: this.route})
  }

}
