import { AfterViewInit, Component, Input, OnDestroy, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTable, MatTableModule } from '@angular/material/table';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { Id, TableDataSource } from '@community-dashboard/rest';
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { animate, state, style, transition, trigger } from '@angular/animations';
import { CollaborationOp, CollaborationOpsService } from '../collaboration-ops.service';

@Component({
  selector: 'app-collaboration-table',
  standalone: true,
  imports: [
    MatInputModule,
    MatFormFieldModule,
    MatIconModule,
    MatButtonModule,
    MatTableModule,
    MatSortModule,
    MatPaginatorModule,
    FormsModule,
    ReactiveFormsModule,
    CommonModule
  ],
  templateUrl: './collaboration-table.component.html',
  styleUrls: ['./collaboration-table.component.css'],
  animations: [
    trigger('detailExpand', [
      state('collapsed', style({height: '0px', minHeight: '0'})),
      state('expanded', style({height: '*'})),
      transition('expanded <=> collapsed', animate('225ms cubic-bezier(0.4, 0.0, 0.2, 1)')),
    ]),
  ],
})
export class CollaborationTableComponent implements AfterViewInit, OnDestroy {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild(MatTable) table!: MatTable<CollaborationOp>;

  @Input() stage!: string

  searchControl = new FormControl('')
  searchSub = this.searchControl.valueChanges.subscribe(
    (v => {
      this.collaborationService.search.next(v ?? '')
    })
  )
  dataSource!: TableDataSource<CollaborationOp>
  count = this.collaborationService.count()

  @Input()
  displayedColumns: string[] = [
    "DATE ADDED",
    // "LOCATION FOUND",
    "title",
    "AGENCY",
    // "OPPORTUNITY DETAILS",
  ]
  columnsToDisplayWithExpand = ['expand', ...this.displayedColumns]
  expanded: {id: Id} | null = null

  constructor(
    private collaborationService: CollaborationOpsService,
  ) {}

  ngAfterViewInit(): void {
    this.dataSource = new TableDataSource(
      this.collaborationService
    )
    this.dataSource.sort = this.sort;
    this.dataSource.paginator = this.paginator;
    this.table.dataSource = this.dataSource;
  }

  ngOnDestroy(): void {
    this.searchSub.unsubscribe()
  }

  toggleRow(row: CollaborationOp) {
    if (this.expanded?.id === row.id) {
      this.expanded = null
    } else {
      this.expanded = {id: row.id}
    }
  }
}
