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
import { EventOp, EventOpsService } from '../event-ops.service';

@Component({
  selector: 'app-event-table',
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
  templateUrl: './event-table.component.html',
  styleUrls: ['./event-table.component.css'],
  animations: [
    trigger('detailExpand', [
      state('collapsed', style({height: '0px', minHeight: '0'})),
      state('expanded', style({height: '*'})),
      transition('expanded <=> collapsed', animate('225ms cubic-bezier(0.4, 0.0, 0.2, 1)')),
    ]),
  ],
})
export class EventTableComponent implements AfterViewInit, OnDestroy {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild(MatTable) table!: MatTable<EventOp>;

  @Input() stage!: string

  searchControl = new FormControl('')
  searchSub = this.searchControl.valueChanges.subscribe(
    (v => {
      this.eventService.search.next(v ?? '')
    })
  )
  dataSource!: TableDataSource<EventOp>
  count = this.eventService.count()

  @Input()
  displayedColumns: string[] = [
    // "DATE ADDED",
    // "WEB LINK",
    "NAME",
    "SPONSOR(S)",
    // "EVENT DATE(S)",
    // "LOCATION(S)",
    // "PRESNTAION SUBMISSION DEADLINE",
    "REGISTRATION DEADLINE",
  ]
  columnsToDisplayWithExpand = ['expand', ...this.displayedColumns]
  expanded: {id: Id} | null = null

  constructor(
    private eventService: EventOpsService,
  ) {}

  ngAfterViewInit(): void {
    this.dataSource = new TableDataSource(
      this.eventService
    )
    this.dataSource.sort = this.sort;
    this.dataSource.paginator = this.paginator;
    this.table.dataSource = this.dataSource;
  }

  ngOnDestroy(): void {
    this.searchSub.unsubscribe()
  }

  // search(d: StudyPromotion) {
  //   const search = this.studyProgressSearchControl.value
  //   if (!search) { return false }
  //   return d.tags.join(' ').toLowerCase().includes(search.toLowerCase()) ||
  //     d.repoName.toLowerCase().includes(search.toLowerCase()) ||
  //     d.useCases.join(' ').toLowerCase().includes(search.toLowerCase()) ||
  //     d.studyType.join(' ').toLowerCase().includes(search.toLowerCase())
  // }

  toggleRow(row: EventOp) {
    if (this.expanded?.id === row.id) {
      this.expanded = null
    } else {
      this.expanded = {id: row.id}
    }
  }
}
