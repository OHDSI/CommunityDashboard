import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CollaborationTableComponent } from './collaboration-table.component';

describe('CollaborationTableComponent', () => {
  let component: CollaborationTableComponent;
  let fixture: ComponentFixture<CollaborationTableComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ CollaborationTableComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(CollaborationTableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
